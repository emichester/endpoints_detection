import numpy as np
import cv2
from imutils import resize
from imutils.contours import sort_contours

from skimage.morphology import skeletonize_3d as skl
from scipy.ndimage import binary_fill_holes as fill
from skimage.morphology import medial_axis as ma
from scipy.ndimage import convolve
from skimage.measure import label, regionprops

# path = 'endpoints_detection/sample.png'
path2 = 'sample.png'
# path2 = 'sample2.png'

try:
    img = cv2.imread(path2, 0)
except:
    img = cv2.imread(path, 0)

orig = img

hini, wini = img.shape

# Some smoothing to get rid of the noise
# img = cv2.bilateralFilter(img, 5, 35, 10)
img = cv2.GaussianBlur(img, (3, 3), 3)
img = resize(img, width=700)

hfin, wfin = img.shape

# Preprocessing to get the shapes
th = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                           cv2.THRESH_BINARY, 35, 11)
# Invert to hightligth the shape
th = cv2.bitwise_not(th)

cv2.imshow('mask', th)
cv2.waitKey(0)

# Text has mostly vertical and right-inclined lines. This kernel seems to
# work quite well
kernel = np.array([[0, 1, 1],
                  [0, 1, 0],
                  [1, 1, 0]], dtype='uint8')

''' Morphological transforms '''
n = 15
for i in range(n):
    th = cv2.morphologyEx(th, cv2.MORPH_DILATE, kernel)
n = 10
for i in range(n):
    th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, kernel)
th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, kernel)
n = 10
for i in range(n):
    th = cv2.morphologyEx(th, cv2.MORPH_ERODE, kernel)

cv2.imshow('mask', th)
cv2.waitKey(0)

''' Area thresholding
    from https://scikit-image.org/docs/stable/user_guide/tutorial_segmentation.html '''
th = fill(th )
th = np.uint8( th*255 )

cv2.imshow('mask', th)
cv2.waitKey(0)

regions = label( th )
sizes = np.bincount(regions.ravel())
mask_sizes = sizes > 1500
mask_sizes[0] = 0
th = mask_sizes[regions]
th = np.uint8( th*255 )

''' Morphological transforms '''
n = 30
for i in range(n):
    th = cv2.morphologyEx(th, cv2.MORPH_DILATE, kernel)
n = 10
for i in range(n):
    th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, kernel)
th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, kernel)
n = 80
for i in range(n):
    th = cv2.morphologyEx(th, cv2.MORPH_ERODE, kernel)

th = fill(th )
th = np.uint8( th*255 )

''' Medial axis 
    https://scikit-image.org/docs/stable/auto_examples/edges/plot_skeleton.html '''
# _, distance = ma(th, return_distance=True)
# th = np.uint8( th*255 )

cv2.imshow('mask', th)
cv2.waitKey(0)


#def contour_sorter(contours):
#    '''Sort the contours by multiplying the y-coordinate and sorting first by
#    x, then by y-coordinate.'''
#    boxes = [cv2.boundingRect(c) for c in contours]
#    cnt = [4*y, x for y, x, , _, _ in ]

# Skeletonize the shapes
# Skimage function takes image with either True, False or 0,1
# and returns and image with values 0, 1.
th = th == 255
th = skl(th)
# th = th.astype(np.uint8)*255 # default method='zhang'
# th = skl(th, method='lee')

''' Eliminating spureus branches
    https://xbuba.com/questions/50341793 '''
def _neighbors_conv(image):
    image = image.astype(np.uint8)
    k = np.array([[1,1,1],[1,0,1],[1,1,1]])
    neighborhood_count = convolve(image,k, mode='constant', cval=1)
    neighborhood_count[~image.astype(np.bool)] = 0
    return neighborhood_count

def break_branches(image):
    tmp = _neighbors_conv(image)
    tmp[tmp==0] = 100
    tmp = tmp < 3
    return tmp

th = break_branches(th/255).astype(np.uint8)*255

cv2.imshow('mask', th)
cv2.waitKey(0)

''' Get skel approx centroid '''
(row,col) = np.nonzero(th)
ctr_approx = ( np.mean( row ) , np.mean( col ) )

''' Get skel centroid '''
dist = 1e10
for (r,c) in zip(row,col):
    tmp = ( (r-ctr_approx[0])**2 + (c-ctr_approx[1])**2 )**0.5
    if tmp <= dist:
        dist = tmp
        ctr = (r,c)

''' Region propperties
    https://stackoverflow.com/questions/42161884/python-how-to-find-all-connected-pixels-if-i-know-an-origin-pixels-position
    https://scikit-image.org/docs/dev/api/skimage.measure.html#regionprops

    # props.bbox # (min_row, min_col, max_row, max_col)
    # props.image # array matching the bbox sub-image
    # props.coordinates # list of (row,col) pixel indices'''
labeled = label( th, background=False, connectivity=2 )
label = labeled[ctr[0],ctr[1]]
rp = regionprops(labeled)
props = rp[label - 1] # background is labeled 0, not in rp

b = props.bbox
th[:,:] = 0
th[ b[0]:b[2] , b[1]:b[3] ] = props.image
th = th.astype( np.uint8 )*255

cv2.imshow('mask', th )
cv2.waitKey(0)

''' Find contours of the skeletons '''
_, contours, _ = cv2.findContours(th.copy(), cv2.RETR_EXTERNAL,
                                  cv2.CHAIN_APPROX_NONE)
# Sort the contours left-to-rigth
contours, _ = sort_contours(contours, )
#
# Sort them again top-to-bottom


def skeleton_endpoints(skel):
    # Function source: https://stackoverflow.com/questions/26537313/
    # how-can-i-find-endpoints-of-binary-skeleton-image-in-opencv
    # make out input nice, possibly necessary
    skel = skel.copy()
    skel[skel != 0] = 1
    skel = np.uint8(skel)

    # apply the convolution
    kernel = np.uint8([[1,  1, 1],
                       [1, 10, 1],
                       [1,  1, 1]])
    src_depth = -1
    filtered = cv2.filter2D(skel, src_depth,kernel)

    # now look through to find the value of 11
    # this returns a mask of the endpoints, but if you just want the
    # coordinates, you could simply return np.where(filtered==11)
    out = np.zeros_like(skel)
    out[np.where(filtered == 11)] = 1
    rows, cols = np.where(filtered == 11)
    coords = list(zip(cols, rows))
    return coords

# List for endpoints
endpoints = []
# List for (x, y) coordinates of the skeletons
skeletons = []



for contour in contours:
    # if cv2.arcLength(contour, True) > 100:
    if cv2.arcLength(contour, True) > 1:
        # Initialize mask
        mask = np.zeros(img.shape, np.uint8)
        # Bounding rect of the contour
        x, y, w, h = cv2.boundingRect(contour)
        mask[y:y+h, x:x+w] = 255
        # Get only the skeleton in the mask area
        mask = cv2.bitwise_and(mask, th)
        # Take the coordinates of the skeleton points
        rows, cols = np.where(mask == 255)
        # Add the coordinates to the list
        skeletons.append(list(zip(cols, rows)))

        # Find the endpoints for the shape and update a list
        eps = skeleton_endpoints(mask)
        endpoints.append(eps)

        # Draw the endpoints
        [cv2.circle(th, ep, 5, 255, 1) for ep in eps]
        # cv2.imshow('mask', mask)
        # cv2.waitKey(500)

# Stack the original and modified
# th = resize(np.hstack((img, th)), 1200)
th = np.hstack((img, th))


#    cv2.waitKey(50)

# TODO
# Walk the points using the endpoints by minimizing the walked distance
# Points in between can be used many times, endpoints only once
cv2.namedWindow('mask', cv2.WINDOW_NORMAL)
cv2.resizeWindow('mask', 800, 800)
cv2.imshow('mask', th)
cv2.waitKey(0)
cv2.destroyAllWindows()

def equivalence( wini, hini, wfin, hfin, xo, yo ):
    y = int(hini*yo/hfin)
    x = int(wini*xo/wfin)
    return x, y

actualendpoints = []

print( 'Resized endpoints %s'%endpoints )
for ep in endpoints[0]:
    actualendpoints.append( equivalence(wini,hini,wfin,hfin,  ep[0] , ep[1] ) )

print( 'Actual endpoints %s'%actualendpoints )