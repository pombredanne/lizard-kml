if __name__ == '__main__':
    import numpy as np
    import matplotlib.pyplot as plt
    import pprint

    a = np.linspace(0, 1, 256).reshape(1,-1)
    a = np.vstack((a,a))

    # Get a list of the colormaps in matplotlib.  Ignore the ones that end with
    # '_r' because these are simply reversed versions of ones that don't end
    # with '_r'
    maps = 'GnBu Greys Oranges autumn ' \
           'Blues cool hot hsv summer ' \
           'YlGn bwr YlOrBr'.split()
    #maps = sorted(m for m in plt.cm.datad if not m.endswith("_r"))
    nmaps = len(maps)
    two_columns = False

    ARR = []

    fig = plt.figure(figsize=(2,3),dpi=100)
    fig.subplots_adjust(top=1, bottom=0, left=0, right=1)

    for i,m in enumerate(maps):
        if two_columns:
            ax = plt.subplot(nmaps/2, 2, i+1)
        else:
            ax = plt.subplot(nmaps, 1, i+1)
        plt.axis("off")
        plt.imshow(a, aspect='auto', cmap=plt.get_cmap(m))
        bb = ax.get_window_extent().bounds
        l = int(bb[0])
        t = int(fig.bbox.height - bb[1] - bb[3])
        r = int(bb[0] + bb[2])
        b = int(fig.bbox.height - bb[1])
        ARR.append((m, (l, t, r, b)))

    fig.savefig("color_maps.png",dpi=fig.dpi,facecolor='white')
    pprint.pprint(ARR)
