import sys
from os import path
from astropy.io import fits
from astropy.io.fits.header import Header
import numpy as np
import os

from core.pluginsystem import Plugin

class Airmass(Plugin):
    """ Pipeline plugin that calculates the airmass for light files
        based on the position header keywords. After some calculations,
        the result is appended to header under the header keyword ?.
    """

    def __init__(self):
        super().__init__()
        self.title = "The Airmass Calculator"
        self.call_level = 500
        self.command_full = "airmass"
        self.description = """ Plugin that calculates the airmass for all light files within
                               an Observation object. Adds this value to the header of this
                               file under the ? header keyword
                           """

    def on_run(self, obs, working_dir, args):
        reduce24 = np.vectorize(self.reduce24_0)
        hourminsec2 = np.vectorize(self.hourminsec)
        hourmin2 = np.vectorize(self.hourmin)
    
        return

    def juliandate(self, date):
        """conversion from gregorian calendar to julian date"""
        year, month, day = date.split('-')
        year = int(year); month = int(month); day = int(day)
        if month == 1 or month == 2:
            year -= 1
            month += 12

        #(for dates later than 15 October 1582)
        A = int(year/100)
        B = 2 - A + int(A/4)
        if year < 0:
            C = int((365.25*year)-0.75)
        else:
            C = int(365.25*year)
        D = int(30.6001*(month+1))

        JD = B + C + D + day + 1720994.5   #julian date
        return JD

    def reduce24_0(self, t):
        """reduces a number in decimal hours into the range 0 to 24"""
        tr = (t/24 - int(t/24))*24    #reduce GST to the range 0-24h
        if tr <= 0:
            tr += 24
        return tr

    def reduce360(self, N):
        """reduces a number to the range 0 to 360"""
        Nr = (N/360 - int(N/360))*360    #reduce N to the range 0-360 degrees
        if Nr <= 0:
            Nr += 360
        return Nr

    def hourminsec(self, ra):
        """"Input is an angle in decimal hours, 
        output is time in hh:mm:ss."""
        ra = reduce24(ra)
        h = int(ra)   #hours
        m = (ra - int(ra))*60   #minutes
        s = (m - int(m))*60    #seconds
        ra2 = f'{h}:{m:.0f}:{s:.2f}' 
        return ra2

    def hourmin(self, ra):
        """"Input is an angle in decimal hours, 
        output is time in hh:mm."""
        ra = reduce24(ra)
        h = int(ra)   #hours
        m = (ra - int(ra))*60   #minutes
        ra2 = f'{h}h {m:.0f}m ' 
        return ra2

    def staralt(self, date, time, RA, DEC):
        """Input are the date("dd/mm/yyyy") and the objects RA/Dec coordinates (name hh:mm:ss.ss ±dd:mm:ss.ss) and time
        Output is the altitude and airmass at the specified *local times"""
        year, month, day = date.split('-')
        year = int(year); month = int(month); day = int(day)
        hours, mnts, sec = time.split(':')
        hours = int(hours); mnts = int(mnts); sec = float(sec)
        time = hours + mnts/60 + sec/3600
        RA = RA/15   #degrees to hours

        long = 6 + 32/60 + 11.2/3600
        lat = 53 + 14/60 + 24.9/3600
        #alt = 25

        TZ = 0  #timezone UTC +02:00

        JD = juliandate(date)     # Julian date

        # UT to GST
        S = JD - 2451545.0
        T = S/36525.0
        T0n = 6.697374558 + (2400.051336*T) + (0.000025862*T*T)
        T0 = reduce24(T0n)

        UT = time - TZ
        UTc = UT*1.002737909
        GST = T0 + UTc
        GST = reduce24(GST)

        #GST to LST
        longh = long/15  #longitude in decimal hours
        LST = reduce24(GST+longh)

        HA = LST - RA
        HA = reduce24(HA)  #hour angle in decimal hours

        #Equatorial to horizon coordinates
        HAr = HA*15 *np.pi/180   # hour angle in radians
        decr = DEC *np.pi/180    #declination in radians
        latr = lat *np.pi/180   #latitude in degrees

        altr = np.arcsin(np.sin(decr)*np.sin(latr) + np.cos(decr)*np.cos(latr)*np.cos(HAr))  # altitude in radians
        altd = altr*180/np.pi
        Azr = np.arccos((np.sin(decr) - np.sin(latr)*np.sin(altr))/(np.cos(latr)*np.cos(altr))) # Azimuth in radians
        Azd = Azr*180/np.pi  #Azimuth in degrees
        Azd = np.where(np.sin(HAr) > 0, Azd, 360 - Azd)

        return altd, Azd

    def airmass(self, alt):
        Z = (90 - alt)*np.pi/180   #zenith distance
        m = (np.cos(Z) + 0.15*(93.885 - Z)**-1.253)**-1   #airmass
        return m

    def set_airmass_hdr(self, filepath):
        """Adds airmass to header of fits file. Input is filepath of fits file"""
        with fits.open(filepath) as hdu:
            hdr = hdu[0].header
            #print(hdr)
            #del hdu[0].header['AIRMCALC']
            imtype = hdu[0].header['IMAGETYP']
            exptime = hdu[0].header['EXPTIME']
            try:
                airm_hdr = hdr['AIRMCALC']
                print("AIRMCALC already present")
            except:
                try:
                    RA = hdr['CRVAL1']
                    DEC = hdr['CRVAL2']
                except:
                    RAstr = hdr['OBJCTRA']
                    DECstr = hdr['OBJCTDEC']

                    hours, mnts, sec = RAstr.split()
                    hours = int(hours); mnts = int(mnts); sec = float(sec)
                    RA = (hours + mnts/60 + sec/3600)*15

                    deg, amnts, asec = DECstr.split()
                    deg = int(deg); amnts = int(amnts); asec = float(asec)
                    DEC = deg + amnts/60 + asec/3600

                #print(RA, DEC)
                Date_Time = hdr['DATE-OBS']
                date, time = Date_Time.split('T')
                #print(date, time)

                #print(staralt(date, time, RA, DEC))
                ALT, AZ = staralt(date, time, RA, DEC)
                airmass_calc = airmass(ALT)

                hdr.set('AIRMCALC', airmass_calc)

    #             #hdu.writeto(out_root+ 'calc_airmass_'+ filename, overwrite = True)
    #             hdu.writeto(out_root+  filename, overwrite = True)
    #             print(filename+ ' Header Generated')

    def add_airmass(self, light_files, working_dir, args):
        """ Function that calculates the airmass for all passed (light) files 
            and adds the result in the header under the keyword 'AIRMCALC'.
            Tries to use Astrometry data if available, otherwise falls 
            back on the original telescope values.
        """
        for file in light_files:
            set_airmass_hdr(file)