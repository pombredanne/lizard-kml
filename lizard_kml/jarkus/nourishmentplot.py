# -*- coding: utf-8 -*-
# <nbformat>3.0</nbformat>

# <codecell>

import bisect
import datetime
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates 

import pandas
import statsmodels.api as sm
import netCDF4
import matplotlib.gridspec

# <codecell>

# Define url's to relevant databases
#mklurl = '/Users/fedorbaart/Downloads/MKL.nc' 
#bklurl = '/Users/fedorbaart/Downloads/BKL_TKL_TND.nc' 
#dfurl = '/Users/fedorbaart/Downloads/DF.nc'
#bwurl = '/Users/fedorbaart/Downloads/DF.nc'
#nourishmenturl = '/Users/fedorbaart/Downloads/suppleties.nc'
#transecturl = '/Users/fedorbaart/Downloads/transect.nc'
#slurl = '/Users/fedorbaart/Downloads/strandlijnen.nc'

#mklurl = 'http://opendap.deltares.nl/thredds/dodsC/opendap/rijkswaterstaat/BKL_TKL_MKL/MKL.nc'  
#bklurl = 'http://opendap.deltares.nl/thredds/dodsC/opendap/rijkswaterstaat/BKL_TKL_MKL/BKL_TKL_TND.nc' 
#dfurl = 'http://opendap.deltares.nl/thredds/dodsC/opendap/rijkswaterstaat/DuneFoot/DF.nc' 
#bwurl = 'http://opendap.deltares.nl/thredds/dodsC/opendap/rijkswaterstaat/strandbreedte/strandbreedte.nc' 
#nourishmenturl = 'http://opendap.deltares.nl/thredds/dodsC/opendap/rijkswaterstaat/suppleties/suppleties.nc' 
#transecturl = 'http://opendap.deltares.nl/thredds/dodsC/opendap/rijkswaterstaat/jarkus/profiles/transect.nc' #'/Users/fedorbaart/Downloads/transect.nc'
#slurl = 'http://opendap.deltares.nl/thredds/dodsC/opendap/rijkswaterstaat/strandlijnen/strandlijnen.nc' #'/Users/fedorbaart/Downloads/transect.nc'

# Function arguments.
transect = 7004100

# <codecell>

def makeshorelinedf(transect, url='http://opendap.deltares.nl/thredds/dodsC/opendap/rijkswaterstaat/strandlijnen/strandlijnen.nc'):
    ds = netCDF4.Dataset(url)
    transectidx = bisect.bisect_left(ds.variables['id'], transect)
    if ds.variables['id'][transectidx] != transect:
        idfound = ds.variables['id'][transectidx]
        ds.close()
        raise ValueError("Could not find shoreline for transect {}, closest is {}".format(transect, idfound))
    year = ds.variables['year'][:]
    time = [datetime.datetime(x, 1,1) for x in year]
    mean_high_water = ds.variables['MHW'][transectidx,:]
    mean_low_water = ds.variables['MLW'][transectidx,:]
    dune_foot = ds.variables['DF'][transectidx,:]
    shorelinedf = pandas.DataFrame(
        data=dict(
            time=time, 
            mean_high_water=mean_high_water, 
            mean_low_water=mean_low_water, 
            dune_foot=dune_foot, 
            year=year
            )
        )
    return shorelinedf


# <codecell>

def maketransectdf(transect, url='http://opendap.deltares.nl/thredds/dodsC/opendap/rijkswaterstaat/jarkus/profiles/transect.nc'):
    # Read dataset and transform to dataframe
    ds = netCDF4.Dataset(url)
    transectidx = bisect.bisect_left(ds.variables['id'],transect)
    if ds.variables['id'][transectidx] != transect:
        idfound = ds.variables['id'][transectidx]
        ds.close()
        raise ValueError("Could not find transect data for transect {}, closest is {}".format(transect, idfound))
    
    alongshore = ds.variables['alongshore'][transectidx]
    areaname = netCDF4.chartostring(ds.variables['areaname'][transectidx])
    mean_high_water = ds.variables['mean_high_water'][transectidx]
    mean_low_water = ds.variables['mean_low_water'][transectidx]
    ds.close()
    
    transectdf = pandas.DataFrame(index=[transect], data=dict(transect=transect, areaname=areaname, mean_high_water=mean_high_water, mean_low_water=mean_low_water))
    return transectdf

# <codecell>

# note that the areaname is a hack, because it is currently missing
def makenourishmentdf(transect, url='http://opendap.deltares.nl/thredds/dodsC/opendap/rijkswaterstaat/suppleties/suppleties.nc', areaname=""):
    """Read the nourishments from the dataset (only store the variables that are a function of nourishment)"""
    
    ds = netCDF4.Dataset(url)
    
    transectidx = bisect.bisect_left(ds.variables['id'],transect)
    if ds.variables['id'][transectidx] != transect:
        idfound = ds.variables['id'][transectidx]
        ds.close()
        raise ValueError("Could not find transect data for transect {}, closest is {}".format(transect, idfound))
    alongshore = ds.variables['alongshore'][transectidx]
    # TODO fix this name, it's missing
    # areaname = netCDF4.chartostring(ds.variables['areaname'][transectidx,:])
    
    alltypes = set(x.strip() for x in netCDF4.chartostring(ds.variables['type'][:]))
   
    
    # this dataset has data on nourishments and per transect. We'll use the per nourishments, for easier plotting. 
    # skip a few variables that have nasty non-ascii (TODO: check how to deal with non-ascii in netcdf)
    vars = [name for name, var in ds.variables.items() if 'survey' not in name and 'other' not in name and 'nourishment' in var.dimensions]
    vardict = {}
    for var in vars:
        if ('date' in var and 'units' in ds.variables[var].ncattrs()):
            # lookup the time variable
            t = netCDF4.netcdftime.num2date(ds.variables[var], ds.variables[var].units)
            vardict[var] = t
        elif 'stringsize' in ds.variables[var].dimensions:
            vardict[var] = netCDF4.chartostring(ds.variables[var][:])
        else:
            vardict[var] = ds.variables[var][:]
    
    # this is specified in the unit decam, which should be dekam according to udunits specs.
    assert ds.variables['beg_stretch'].units == 'decam'
    ds.close()
    # Put the data in a frame
    nourishmentdf = pandas.DataFrame.from_dict(vardict)
    # Compute nourishment volume in m3/m
    nourishmentdf['volm'] = nourishmentdf['vol']/(10*(nourishmentdf['end_stretch']-nourishmentdf['beg_stretch']))
    
    # simplify for colors
    typemap = {'':'strand', 
        'strandsuppletie':'strand', 
        'dijkverzwaring':'duin', 
        'strandsuppletie banket':'strand', 
        'duinverzwaring':'duin', 
        'strandsuppletie+vooroever':'overig', 
        'Duinverzwaring':'duin',
        'duin':'duin', 
        'duinverzwaring en strandsuppleti':'duin', 
        'vooroever':'vooroever', 
        'zeewaartse duinverzwaring':'duin', 
        'banket': 'strand' ,
        'geulwand': 'geulwand', 
        'anders':'overig', 
        'landwaartse duinverzwaring':'duin', 
        'depot':'overig', 
        'vooroeversuppletie':'vooroever', 
        'onderwatersuppletie':'vooroever', 
        'geulwandsuppletie':'geulwand'
        }
    beachcolors = {
              'duin': 'peru',
              'strand': 'khaki',
              'vooroever': 'aquamarine',
              'geulwand': 'lightseagreen',
              'overig': 'grey'
        }
    # Filter by current area and match the area
    filter = reduce(np.logical_and, [
        alongshore >= nourishmentdf.beg_stretch,  
        alongshore < nourishmentdf.end_stretch, 
        nourishmentdf['kustvak'].apply(str.strip)==areaname.tostring().strip()
        ])
    
    nourishmentdfsel = nourishmentdf[filter]
    return nourishmentdfsel


# <codecell>

def makemkldf(transect, url='http://opendap.deltares.nl/thredds/dodsC/opendap/rijkswaterstaat/BKL_TKL_MKL/MKL.nc'):
    # Now read the mkl data.
    ds = netCDF4.Dataset(url)
    # Use bisect to speed things up
    transectidx = bisect.bisect_left(ds.variables['id'], transect)
    vars = [name for name, var in ds.variables.items() if var.dimensions == ('time', 'alongshore')]
    # Convert all variables that are a function of time to a dataframe
    vardict = dict((var, ds.variables[var][:,transectidx]) for var in vars)
    vardict['time'] = netCDF4.netcdftime.num2date(ds.variables['time'], ds.variables['time'].units)
    # Deal with nan's in an elegant way:
    mkltime = ds.variables['time_MKL'][:,transectidx]
    mkltime = np.ma.masked_array(mkltime, mask=np.isnan(mkltime))
    vardict['time_MKL'] = netCDF4.netcdftime.num2date(mkltime, ds.variables['time_MKL'].units)
    ds.close()
    mkldf =  pandas.DataFrame(vardict)
    mkldf = mkldf[np.logical_not(pandas.isnull(mkldf['time_MKL']))]
    return mkldf


# <codecell>

def makebkldf(transect, url='http://opendap.deltares.nl/thredds/dodsC/opendap/rijkswaterstaat/BKL_TKL_MKL/BKL_TKL_TND.nc' ):
    # Now read the mkl data.
    ds = netCDF4.Dataset(url)
    # Use bisect to speed things up
    transectidx = bisect.bisect_left(ds.variables['id'], transect)
    vars = [name for name, var in ds.variables.items() if var.dimensions == ('time', 'alongshore')]
    # Convert all variables that are a function of time to a dataframe
    vardict = dict((var, ds.variables[var][:,transectidx]) for var in vars)
    vardict['time'] = netCDF4.netcdftime.num2date(ds.variables['time'], ds.variables['time'].units)
    ds.close()
    bkldf =  pandas.DataFrame(vardict)
    return bkldf


# <codecell>

def makebwdf(transect, url='http://opendap.deltares.nl/thredds/dodsC/opendap/rijkswaterstaat/strandbreedte/strandbreedte.nc'):
    # Now read the beachwidth data.
    ds = netCDF4.Dataset(url)
    # Use bisect to speed things up
    transectidx = bisect.bisect_left(ds.variables['id'], transect)
    vars = [name for name, var in ds.variables.items() if var.dimensions == ('time', 'alongshore')]
    # Convert all variables that are a function of time to a dataframe
    vardict = dict((var, ds.variables[var][:,transectidx]) for var in vars)
    vardict['time'] = netCDF4.netcdftime.num2date(ds.variables['time'], ds.variables['time'].units)
    ds.close()
    bwdf =  pandas.DataFrame(vardict)
    return bwdf

# <codecell>

def makedfdf(transect, url='http://opendap.deltares.nl/thredds/dodsC/opendap/rijkswaterstaat/DuneFoot/DF.nc'):
    # Now read the dunefoot data.
    ds = netCDF4.Dataset(url)
    
    # Use bisect to speed things up
    transectidx = bisect.bisect_left(ds.variables['id'], transect)
    vars = [name for name, var in ds.variables.items() if var.dimensions == ('alongshore', 'time')]
    # Convert all variables that are a function of time to a dataframe
    # Note inconcsiste dimension ordering
    vardict = dict((var, ds.variables[var][transectidx,:]) for var in vars)
    vardict['time'] = netCDF4.netcdftime.num2date(ds.variables['time'], ds.variables['time'].units)
    ds.close()
    dfdf =  pandas.DataFrame(vardict)
    return dfdf


# <codecell>

def makedfs(transect):
    shorelinedf = makeshorelinedf(transect)
    transectdf = maketransectdf(transect)
    nourishmentdf = makenourishmentdf(transect, areaname=transectdf['areaname'].irow(0))
    mkldf = makemkldf(transect)
    bkldf = makebkldf(transect)
    bwdf = makebwdf(transect)
    dfdf = makedfdf(transect)
    return dict(
        shorelinedf=shorelinedf,
        transectdf=transectdf,
        nourishmentdf=nourishmentdf,
        mkldf=mkldf,
        bkldf=bkldf,
        bwdf=bwdf,
        dfdf=dfdf
        )

# <codecell>

def combinedplot(dfs):
    """Create a combined plot of the coastal data"""
    
    shorelinedf = dfs['shorelinedf']
    transectdf = dfs['transectdf']
    nourishmentdf = dfs['nourishmentdf']
    mkldf = dfs['mkldf']
    bkldf = dfs['bkldf']
    bwdf = dfs['bwdf']
    dfdf = dfs['dfdf']

    transect = transectdf['transect'].irow(0)
    areaname = transectdf['areaname'].irow(0)
    
    # Plot the results.

    fig = plt.figure(figsize=(10,10))
    # We define a grid of 3 areas 
    gs = matplotlib.gridspec.GridSpec(4, 1, height_ratios=[5, 2, 2, 2]) 
    gs.update(hspace=0.1)
    
    # Some common style properties, also store they style information file for ggplot style in the directory where the script is.
    props = dict(linewidth=2, alpha=0.7, markeredgewidth=0, markersize=8, linestyle='-', marker='.')


    #Figuur 1: momentane kustlijn / te toetsenkustlijn / basiskustlijn, oftewel onderstaand tweede figuur. Bij voorkeur wel in het Nederlands en volgens mij klopt de tekst bij de as nu niet (afstand tot RSP (meters))
    
    # The first axis contains the coastal indicators related to volume
    # Create the axis, based on the gridspec

    ax1 = fig.add_subplot(gs[0])
    # Set the main title
    ax1.set_title('Kengetallen van de toestand van de kust\ntransect %d (%s)' % (transect, str(areaname).strip()))
    # Plot the three lines
    ax1.plot(matplotlib.dates.date2num(mkldf['time_MKL']), mkldf['momentary_coastline'], label='momentane kustlijn', **props)
    ax1.plot(bkldf['time'], bkldf['basal_coastline'], label='basiskustlijn', **props)
    ax1.plot(bkldf['time'], bkldf['testing_coastline'], label='te toetsenkustlijn', **props)
    
    # Plot the legend. This uses the label
    ax1.legend(loc='upper left')
    # Show the y axis label
    ax1.set_ylabel('Afstand [m]')
    # Hide the ticks for this axis (can't use set_visible on xaxis because it is shared)
    try:
        for label in ax1.xaxis.get_ticklabels():
            label.set_visible(False)
    except ValueError, e:
        # No date set on axes, because of no data. No worries...
        pass

    
    # Figuur 2: duinvoet / hoogwater / laagwater, vanaf (ongeveer) 1848 voor raai om de kilometer. Voor andere raaien vanaf 1965 (Jarkus) 
    ax2 = fig.add_subplot(gs[1], sharex=ax1)
    ax2.plot(dfdf['time'], dfdf['dune_foot_rsp'], label='duinvoet positie', **props)
    ax2.plot(shorelinedf['time'], shorelinedf['dune_foot'], label='historische duinvoet positie', **props)
    ax2.plot(shorelinedf['time'], shorelinedf['mean_high_water'], label='historische hoogwater positie', **props)
    ax2.plot(shorelinedf['time'], shorelinedf['mean_high_water'], label='historische laagwater positie', **props)
    ax2.legend(loc='best')
    # Look up the location of the tick labels, because we're removing all but the first and last.
    locs = [ax2.yaxis.get_ticklocs()[0], ax2.yaxis.get_ticklocs()[-1]]
    # We don't want too much cluttering
    ax2.yaxis.set_ticks(locs)
    
    # Again remove the xaxis labels
    try:
        for label in ax2.xaxis.get_ticklabels():
            label.set_visible(False)
    except ValueError, e:
        # No dates no problem
        pass
    ax2.set_ylabel('Afstand [m]') 
    
    # Figuur 3 strandbreedte bij hoogwater / strandbreedte bij laagwater (ook vanaf ongeveer 1848 voor raai om de kilometer, voor andere raaien vanaf 1965 )
    # Create another axis for the width and position parameters
    # Share the x axis with axes ax1
    ax3 = fig.add_subplot(gs[2], sharex=ax1)
    # Plot the 3 lines
    '''
    ax3.fill_between(np.asarray(bwdf['time']), np.asarray(bwdf['beach_width_at_MLW']), np.asarray(bwdf['beach_width_at_MHW']), alpha=0.3, color='black')
    ax3.plot(bwdf['time'], bwdf['beach_width_at_MHW'], label='strandbreedte MHW', **props)
    ax3.plot(bwdf['time'], bwdf['beach_width_at_MLW'], label='strandbreedte MLW', **props)
    '''
    ax3.plot(dfdf['time'], dfdf['dune_foot_rsp'], label='duinvoet positie', **props)
    # Dune foot is position but relative to RSP, so we can call it a width
    ax3.set_ylabel('Breedte [m]') 
    # Look up the location of the tick labels, because we're removing all but the first and last.
    locs = [ax3.yaxis.get_ticklocs()[0], ax3.yaxis.get_ticklocs()[-1]]
    # We don't want too much cluttering
    ax3.yaxis.set_ticks(locs)
    ax3.yaxis.grid(False)
    # Again remove the xaxis labels
    try:
        for label in ax3.xaxis.get_ticklabels():
            label.set_visible(False)
    except ValueError, e:
        # No dates no problem
        pass
    # Place the legend
    ax3.legend(loc='upper left')
    
    
    # Figuur 4 uitgevoerde suppleties (laatste figuure onderaan), tekst bij de as bij voorkeur Volume (m3/m)
    
    # Create the third axes, again sharing the x-axis
    ax4 = fig.add_subplot(gs[3],sharex=ax1)
    # We need to store labels and a "proxy artist". 
    proxies = []
    labels = []
    # Loop over eadge row, because we need to look up colors (bit of a hack)
    for i, row in nourishmentdf.iterrows():
        # Look up the color based on the type of nourishment
        color = beachcolors[typemap[row['type'].strip()]]
        # Strip spaces
        label = row['type'].strip()
        # Common properties
        props = dict(alpha=0.7, linewidth=2)
        # Plot a bar per nourishment
        ax4.fill_betweenx([0,row['volm']],row['beg_date'], row['end_date'], edgecolor=color, color=color, **props)
        if label not in labels:
            # Fill_between's are not added with labels. 
            # So we'll create a proxy artist (a non plotted rectangle, with the same color)
            # http://matplotlib.org/users/legend_guide.html
            proxy = matplotlib.patches.Rectangle((0, 0), 1, 1, facecolor=color, **props)
            proxy.set_label(label)
            proxies.append(proxy)
            labels.append(label)
    # Only use first and last tick label
    locs = [ax4.yaxis.get_ticklocs()[0], ax4.yaxis.get_ticklocs()[-1]]
    ax4.yaxis.set_ticks(locs)
    ax4.yaxis.grid(False)
    #ax3.yaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter('%.0f'))
    ax4.set_ylabel('Volume [m3/m]')
    ax4.set_xlabel('Tijd [jaren]')
    # This one we want to see
    ax4.xaxis.set_visible(True)
    # Show dates at decenia
    ax4.xaxis.set_major_locator(matplotlib.dates.YearLocator(base=10))
    # Now we plot the proxies with corresponding legends.
    legend = ax4.legend(proxies, labels, loc='upper left')
    return fig


# <codecell>

dfs = makedfs(transect)
fig = combinedplot(dfs)


# <codecell>


# <codecell>

