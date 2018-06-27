import numpy as np
from scipy import misc
from scipy import signal
import argparse
import time
from matplotlib import pyplot as plt
import cv2

from frame_interp import interpolate_frame
from frame_interp import decompose
from frame_interp import shift_correction
from frame_interp import unwrap
from frame_interp import reconstruct_image

def convert_back_pyr(phase, im_stru):
    reconstructed=[]
    for i in range(3):
        f_dimension=[]
        start=0
        stop=0
        for ph in im_stru['phase'][i]:
            dim=ph.shape
            stop+=(dim[0]*dim[1])
            #print(stop)
            pyramid=phase[start:stop, i]
            start=stop
            f_dimension.append(np.reshape(pyramid, dim))
        reconstructed.append(f_dimension)
    return np.array(reconstructed)

def reconstruct_pyr(arr, pind):
    reconstructed=[]
    for i in range(3):
        f_dimension=[]
        start=0
        stop=0
        for dim in pind:
            stop+=(dim[0]*dim[1])
            #print(stop)
            pyramid=arr[i, start:stop]
            start=stop
            f_dimension.append(np.reshape(pyramid, dim))
        reconstructed.append(f_dimension)
    return np.array(reconstructed)

def convert_back_pyr_1d(phase, im_stru):
    f_dimension=[]
    start=0
    stop=0
    for ph in im_stru['phase'][0]:
        dim=ph.shape
        stop+=(dim[0]*dim[1])
        #print(stop)
        pyramid=phase[start:stop]
        start=stop
        f_dimension.append(np.reshape(pyramid, dim))
    return np.array(f_dimension)

def append_all(high, new, low):
    out_pyr=[]
    for i in range(3):
        high_dim=high[i].flatten()
        high_dim=np.append(high_dim, new[:,i])
        high_dim=np.append(high_dim, low[i].flatten())
        out_pyr.append(high_dim)
    return np.asarray(out_pyr)

def phase_diff_filter(phase_diff, filter):
    for i in range(filter.shape[0]):
        for j in range(phase_diff.shape[1]):
            for pyr in range(phase_diff.shape[2]):
                phase_diff[i,j,pyr]=phase_diff[i,j,pyr]*filter[i]
    return phase_diff

def repmat(array, n):
    ret_array=[]
    for i in range(n):
        ret_array.append(array)
    return np.asarray(ret_array)

def roll_and_append(arr1, arr2):
    arr1=arr1[1:,:].tolist()
    arr1.append(arr2)
    return np.asarray(arr1)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    #parser.add_argument('img1', type=str, help='Path to first frame.')
    #parser.add_argument('img2', type=str, help='Path to second frame.')
    #parser.add_argument('--n_frames', '-n', type=int, default=1, help='Number of new frames.')
    #parser.add_argument('--show', '-sh', type=int, default=0, help='Display result.')
    #parser.add_argument('--save', '-s', type=int, default=0, help='Save interpolated images.')
    #parser.add_argument('--save_path', '-p', type=str, default='', help='Output path.')
    args = parser.parse_args()
    xp = np

    #img1 = misc.imread(args.img1)
    #img2 = misc.imread(args.img2)

    print('start')
    start = time.time()
    print(cv2.__version__)
    cap = cv2.VideoCapture('syn_ball.avi')
    vidHeight = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    vidWidth = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    nChannels = 3
    frame_rate = cap.get(cv2.CAP_PROP_FPS)
    fr_num = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter('output.avi', fourcc, frame_rate, (vidWidth, vidHeight))

    nOrientations = 8
    tWidth = 1
    limit = 0.2
    min_size = 15
    max_levels = 23
    py_level = 4
    scale = 0.5 ** (1 / py_level)
    n_scales = min(np.ceil(np.log2(min((vidHeight, vidWidth))) / np.log2(1. / scale) -
                           (np.log2(min_size) / np.log2(1 / scale))).astype('int'), max_levels)
    motion_freq_es = 10 / 3
    time_interval = 1 / 4 * 1 / motion_freq_es
    amp_factor = 5
    # motionAMP
    frame_interval = np.ceil(frame_rate * time_interval).astype(int)
    windowSize = 2 * frame_interval
    norder = windowSize * 2

    # TEMPKERNEL - INT

    signalLen = 2 * windowSize
    sigma = frame_interval / 2
    x = np.linspace(-signalLen / 2, signalLen / 2, signalLen + 1)
    kernel = np.zeros(x.shape, dtype=float)

    INT_kernel = kernel
    INT_kernel[frame_interval] = 0.5
    INT_kernel[2 * frame_interval] = -1
    INT_kernel[3 * frame_interval] = 0.5
    kernel = -INT_kernel / sum(abs(INT_kernel))
    kernel = np.reshape(kernel, (13, 1))
    ret, im = cap.read()
    im = cv2.cvtColor(im, cv2.COLOR_BGR2Lab)
    im_stru = decompose(im, n_scales, nOrientations, tWidth, scale, n_scales, xp)
    phase_im_1=im_stru['phase'].copy()
    phase_im=repmat(phase_im_1, 13)
    cv2.imwrite("izhod.png", im)

    for ii in range(2, 50):
        ret, im = cap.read()
        im = cv2.cvtColor(im, cv2.COLOR_BGR2Lab)
        #cv2.imwrite('frameorg'+str(ii)+'.png', im1)
        im_stru = decompose(im, n_scales, nOrientations, tWidth, scale, n_scales, xp)
        fac = 1.5
        phase_im_1=np.array(im_stru['phase'])
        phase_im=roll_and_append(phase_im, phase_im_1)
        #diff=np.asarray(phase_im[norder, :] - phase_im[norder - 1, :])
        diff=np.asarray(phase_im[norder]-phase_im[norder-1])
        diff2=np.asarray(phase_im[norder-1]-phase_im[norder])
        #diff2=np.asarray(phase_im[norder-1, :] - phase_im[norder, :])
        for i in range(diff.shape[0]):
            for j in range(diff.shape[1]):
                mask=(diff[i,j]>(fac*np.pi)).astype(np.float64)
                phase_im[norder, i,j] = phase_im[norder, i, j] - mask*(2.*np.pi)
                mask=(diff2[i,j]>(fac*np.pi)).astype(np.float64)
                phase_im[norder, i, j] = phase_im[norder, i, j] + mask * (2. * np.pi)

        print("temporal processing frame ",ii)
        phase_im_conv=phase_diff_filter(phase_im, kernel)
        phase_filt=np.sum(phase_im_conv, axis=0)
        ph2mag=np.asarray(phase_im_1)
        amp_im2=np.asarray(im_stru['amplitude'])
        pind=im_stru['pyramids'][0].pyrSize

        phase_diff=phase_filt.copy()
        phase_diff_original=phase_diff.copy()
        for ic in range(phase_diff.shape[0]):
            phase_diff[ic] = shift_correction(phase_diff[ic], im_stru['pyramids'][ic], scale,limit)
            tmp_phase_diff=[item for i in phase_diff[ic] for it in i for item in it]
            tmp_phase_diff_org=[item for i in phase_diff_original[ic] for it in i for item in it]
            unwrappedPhaseDifference = unwrap(np.array([tmp_phase_diff, tmp_phase_diff_org]))
            phase_diff[ic]=convert_back_pyr_1d(unwrappedPhaseDifference[1,:], im_stru)

        # Motion magnification
        print("motion magnification frame")
        for i in range(amp_im2.shape[0]):
            for j in range(amp_im2.shape[1]):
                expp=np.exp(1j*(ph2mag[i,j]+amp_factor*phase_diff[i,j]))
                amp_im2[i, j] = amp_im2[i, j] * expp

        amp_im2=amp_im2.tolist()
        for i in range(len(amp_im2)):
            amp_im2[i].insert(0, im_stru['high_pass'][i].astype(np.complex128))
            amp_im2[i].append(im_stru['low_pass'][i].astype(np.complex128))


        for ch in range(3):
            im_stru['pyramids'][ch].pyr = amp_im2[ch]

        rec_img = reconstruct_image(im_stru)
        rec_img = rec_img*255
        rec_img = rec_img.astype(np.uint8)
        rec_img = cv2.cvtColor(rec_img, cv2.COLOR_Lab2BGR)
        cv2.imwrite('frame'+str(ii)+'.png', rec_img)
        out.write(rec_img)
    cap.release()
    out.release()
    print('Took %.2fm' % ((time.time() - start) / 60.))

