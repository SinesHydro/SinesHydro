# -*- coding: utf-8 -*-
"""
Created on Wed Sep 23 16:14:12 2020

@author: Daniel
"""

import os,sys
import pandas as pd
import numpy as np
import warnings
from scipy.optimize import curve_fit
from scipy.linalg import svdvals
from scipy.stats import linregress
from scipy.signal import csd
from scipy.optimize import least_squares
from mpmath import ker, kei, power, sqrt

from .. import utils
from ..models import const

# static class
class Analysis(object):
    #def __init__(self, *args, **kwargs):
    #    pass

    @staticmethod
    def BE_average_of_ratios(X, Y):
        '''
        Calculate instantaneous barometric efficiency using the average of ratios method, a time domain solution.

        Parameters
        ----------
        X : N x 1 numpy array
            barometric pressure data,  provided as either measured values or as temporal derivatives.
        Y : N x 1 numpy array
            groundwater pressure data, provided as either measured values or as temporal derivatives.

        Returns
        -------
        scalar
            Instantaneous barometric efficiency calculated as the mean ratio of measured values or temporal derivatives.

        Notes
        -----
            ** Need to come up with a better way to avoid division by zero issues and similar
            -> maybe this works: https://stackoverflow.com/questions/26248654/how-to-return-0-with-divide-by-zero
        '''
        result = np.mean(np.divide(Y, X, out=np.zeros_like(Y), where=X!=0))
        return result

    @staticmethod
    def BE_median_of_ratios(X, Y):
        '''
        Inputs:
            X - barometric pressure data,  provided as either measured values or as temporal derivatives. Should be an N x 1 numpy array.
            Y - groundwater pressure data, provided as either measured values or as temporal derivatives. Should be an N x 1 numpy array.

        Outputs:
            result      - scalar. Instantaneous barometric efficiency calculated as the median ratio of measured values or temporal derivatives.
        '''
        result = np.median(np.divide(Y, X, out=np.zeros_like(Y), where=X!=0))
        return result

    @staticmethod
    def BE_linear_regression(X, Y):
        '''
        Inputs:
            X - barometric pressure data,  provided as either measured values or as temporal derivatives. Should be an N x 1 numpy array.
            Y - groundwater pressure data, provided as either measured values or as temporal derivatives. Should be an N x 1 numpy array.

        Outputs:
            result      - scalar. Instantaneous barometric efficiency calculated as a linear regression based on measured values or temporal derivatives.
        '''
        result = np.linregress(Y, X)[0]
        return result

    @staticmethod
    def BE_Clark(X, Y):
        '''
        Inputs:
            X - barometric pressure data,  provided as either measured values or as temporal derivatives. Should be an N x 1 numpy array.
            Y - groundwater pressure data, provided as either measured values or as temporal derivatives. Should be an N x 1 numpy array.

        Outputs:
            result      - scalar. Instantaneous barometric efficiency calculated using the Clark (1967) method using measured values or temporal derivatives.
        '''
        sX, sY = [0], [0]
        for x,y in zip(X, Y):
            sX.append(sX[-1]+abs(x))
            if x==0:
                sY.append(sY[-1])
            elif np.sign(y)==np.sign(x):
                sY.append(sY[-1]+abs(y))
            elif np.sign(y)!=np.sign(x):
                sY.append(sY[-1]-abs(y))
        result = linregress(sX, sY)[0]
        return result

    @staticmethod
    def BE_Davis_and_Rasmussen(X, Y):
        '''
        Calculate instantaneous barometric efficiency using the Davis and Rasmussen (1993) method, a time domain solution.

        Parameters
        ----------
        X : N x 1 numpy array
            barometric pressure data,  provided as either measured values or as temporal derivatives.
        Y : N x 1 numpy array
            groundwater pressure data, provided as either measured values or as temporal derivatives.

        Returns
        -------
        result : scalar
            Instantaneous barometric efficiency calculated using the Davis and Rasmussen (1993) method using measured values or temporal derivatives.

        Notes
        -----
            ** Work in progress - just need to marry the D&R algorithm with the automated segmenting algorithm
        '''
        cSnum    = np.zeros(1)
        cSden    = np.zeros(1)
        cSabs_dB = np.zeros(1)
        cSclk_dW = np.zeros(1)
        dB       = -np.diff(X)
        n        =  len(dB)
        j        =  len(dB[dB>0.])-len(dB[dB<0.])
        Sraw_dB  =  np.sum(dB)
        Sabs_dB  =  np.sum(np.abs(dB))
        dW       =  np.diff(Y)
        Sraw_dW  =  np.sum(dW)
        Sclk_dW  = np.zeros(1)
        for m in range(len(dW)):
            if np.sign(dW[m])==np.sign(dB[m]):
                Sclk_dW += np.abs(dW[m])
            elif np.sign(dW[m])!=np.sign(dB[m]):
                Sclk_dW -= np.abs(dW[m])
        cSnum    += (float(j)/float(n))*Sraw_dW
        cSden    += (float(j)/float(n))*Sraw_dB
        cSabs_dB += Sabs_dB
        cSclk_dW += Sclk_dW
        result = ((cSclk_dW/cSabs_dB-cSnum/cSabs_dB)/(1.-cSden/cSabs_dB))
        return result

    @staticmethod
    def BE_Rahi(X, Y):
        '''
        Calculate instantaneous barometric efficiency using the Clark (1967) method, a time domain solution.

        Parameters
        ----------
        X : N x 1 numpy array
            barometric pressure data,  provided as either measured values or as temporal derivatives.
        Y : N x 1 numpy array
            groundwater pressure data, provided as either measured values or as temporal derivatives.

        Returns
        -------
        result : scalar
            Instantaneous barometric efficiency calculated using the Rahi (2010) method using measured values or temporal derivatives.

        Notes
        -----
            ** Need to check that Rahi's rules are implemented the right way around.
        '''
        sX, sY = [0], [0]
        for x,y in zip(X, Y):
            if (np.sign(y)==np.sign(x)) & (abs(y)<abs(x)):
                sY.append(sY[-1]+abs(y))
                sX.append(sX[-1]+abs(x))
            else:
                sY.append(sY[-1])
                sX.append(sX[-1])
        result = np.divide(sY[-1], sX[-1], out=np.zeros_like(Y), where=X!=0)
        return result

    @staticmethod
    def BE_Quilty_and_Roeloffs(X, Y, freq, nperseg, noverlap):
        '''


        Parameters
        ----------
        X : N x 1 numpy array
            barometric pressure data,  provided as either measured values or as temporal derivatives.
        Y : N x 1 numpy array
            groundwater pressure data, provided as either measured values or as temporal derivatives.
        freq : float
            The frequency of interest.
        nperseg : int
            The number of data points per segment.
        noverlap : int
            The amount of overlap between data points used when calculating power and cross spectral density outputs.

        Returns
        -------
        result : scalar
            Instantaneous barometric efficiency calculated using the Quilty and Roeloffs (1991) method using measured values or temporal derivatives.

        Notes
        -----
            ** Need to check that Rojstaczer's (or Q&R's) implementation was averaged over all frequencies
        '''

        csd_f, csd_p = csd(X, Y, fs=freq, nperseg=nperseg, noverlap=noverlap) #, scaling='density', detrend=False)
        psd_f, psd_p = csd(X, X, fs=freq, nperseg=nperseg, noverlap=noverlap) #, scaling='density', detrend=False)
        result = np.mean(np.abs(csd_p)/psd_p)
        return result

    @staticmethod
    def BE_Rau(BP_s2:complex, ET_m2:complex, ET_s2:complex, GW_m2:complex, GW_s2:complex, amp_ratio:float=1):
        # Equation 9, Rau et al. (2020), doi:10.5194/hess-24-6033-2020
        GW_ET_s2 = (GW_m2 / ET_m2) * ET_s2
        GW_AT_s2 = GW_s2 - GW_ET_s2
        BE = (1/amp_ratio)*np.abs(GW_AT_s2 / BP_s2)
        
        # a phase check ...
        GW_ET_m2_dphi = np.angle(GW_m2 / ET_m2)
        if ((amp_ratio == 1) and (np.abs(GW_ET_m2_dphi) > 5)):
            warnings.warn("Attention: The phase difference between GW and ET is {.1f}°. BE could be affected by amplitude damping!".format(np.degrees(GW_ET_m2_dphi)))
        
        return BE

    @staticmethod
    def BE_Acworth(BP_s2:complex, ET_m2:complex, ET_s2:complex, GW_m2:complex, GW_s2:complex):
        # Calculate BE values
        # Equation 4, Acworth et al. (2016), doi:10.1002/2016GL071328
        BE = (np.abs(GW_s2)  + np.abs(ET_s2) * np.cos(np.angle(BP_s2) - np.angle(ET_s2)) * (np.abs(GW_m2) / np.abs(ET_m2))) / np.abs(BP_s2)
        
        # provide a user warning ...
        if (np.abs(GW_m2) > np.abs(GW_s2)):
            warnings.warn("Attention: There are significant ET components present in the GW data. Please use the 'rau' method for more accurate results!")
        
        return BE


    @staticmethod
    def K_Ss_estimate(ET_m2:complex, ET_s2:complex, GW_m2:complex, GW_s2:complex, case_rad, scr_len, scr_rad, scr_depth):
        # !!! need borehole construction parameters
        # !!! need to make sure that ET data has strain units!!!
        
        # M2 frequency
        f_m2 = const['_etfqs']['M2']
        
        amp = np.abs(GW_m2 / ET_m2)
        # amp = GW_amp_M2 / ETstr_man #
        print("Amplitude response / areal strain sensitivity: {:.3f}".format(amp))
        
        #ET phase difference
        phase = np.angle(GW_m2 / ET_m2)
        print("delta_ET-GW: {:.4f} [rad], {:.4f} [°]".format(phase, np.degrees(phase)))
        
        results = {'GW-ET_Ar': amp, 'GW-ET_dphi': phase}
        
        #%% use the Hsieh model
        if (phase < 0.01):
            global Ker, Kei, power, sqrt
            Ker = np.frompyfunc(ker, 2, 1)
            Kei = np.frompyfunc(kei, 2, 1)
            power = np.frompyfunc(power, 2, 1)
            sqrt = np.frompyfunc(sqrt, 1, 1)
            
            # the horizontal flow / negative phase model
            def et_hflow(K, S_s, r_w=0.1, r_c=0.1, b=2, f=f_m2):
                global Ker, Kei, power, sqrt
                # create numpy function from mpmath
                # https://stackoverflow.com/questions/51971328/how-to-evaluate-a-numpy-array-inside-an-mpmath-fuction
                D_h = K / S_s
                omega = 2*np.pi*f
                tmp = omega / D_h
                # prevent errors from negative square roots
                if (tmp >= 0):
                    T = K*b
                    sqrt_of_2 = sqrt(2)
                    alpha_w = r_w * sqrt(tmp)
                    ker_0_alpha_w = Ker(0, alpha_w)
                    ker_1_alpha_w = Ker(1, alpha_w)
                    kei_0_alpha_w = Kei(0, alpha_w)
                    kei_1_alpha_w = Kei(1, alpha_w)
                    denom = power(ker_1_alpha_w, 2) + power(kei_1_alpha_w, 2)
                    Psi = - (ker_1_alpha_w - kei_1_alpha_w) / (sqrt_of_2 * alpha_w * denom)
                    Phi = - (ker_1_alpha_w + kei_1_alpha_w) / (sqrt_of_2 * alpha_w * denom)
                    E = np.float64(1 - (((omega*power(r_c, 2))/(2*T)) * (Psi*ker_0_alpha_w + Phi*kei_0_alpha_w)))
                    F = np.float64((((omega*power(r_c,2))/(2*T)) * (Phi*ker_0_alpha_w - Psi*kei_0_alpha_w)))
                    Ar = (E**2 + F**2)**(-0.5)
                    dPhi = -np.arctan(F/E)
                    return Ar, dPhi
                else:
                    return np.Inf, np.Inf
            
            def fit_amp_phase(props, amp, phase, r_c, r_w, scr_len, freq):
                #print(props)
                K, S_s = props
                Ar, dPhi = et_hflow(K, S_s, r_c, r_w, scr_len, freq)
                res_amp = amp*S_s - Ar
                res_phase = phase - dPhi
                error = np.asarray([res_amp,res_phase])
            #    print(error)
                return error
            
            #%%
            print("-------------------------------------------------")
            print('Joint inversion of K and Ss:')
            # least squares fitting
            fit =  least_squares(fit_amp_phase, [1e-4*24*3600, 1e-4], args=(amp, phase, case_rad, scr_rad, scr_len, f_m2), xtol=1e-30, ftol=1e-30, gtol=1e-16, method='lm')
            print(fit)
            
            # change units to m and s
            K = fit.x[0]/24/3600
            Ss = fit.x[1]
            
            print("-------------------------------------------------")
            if (fit.status > 0):
                print("Hydraulic conductivity: {:.2e} m/s".format(K))
                print("Specific storage: {:.2e} 1/m".format(Ss))
                print("-------------------------------------------------")
                Ar, dPhi = et_hflow(fit.x[0], fit.x[1], r_c=case_rad, r_w=scr_rad, b=scr_len, f=f_m2)
                print("Amplitude ratio: {:.3f} [-]".format(Ar))
                print("Phase shift: {:.3f} [rad], {:.2f}°".format(dPhi, np.degrees(dPhi)))
                print("-------------------------------------------------")
                
                results.update({'K': K, 'Ss': Ss, 'Model': 'Hsieh', 'redidual': 'XXXX', 'screen_radius': scr_rad, 'casing_radius': case_rad, 'screen_length': scr_len})
            else:
                print('Failed!')
        
        #%% use the Wang model
        else:
            # the vertical flow / positive phase model
            def vflow_amp(K, S_s, z=20, f=f_m2):
                D_h = K / S_s
                omega = 2*np.pi*(f/24/3600)
                delta = np.sqrt(2*D_h/omega)
                return (np.sqrt(1 - 2*np.exp(-z/delta) * np.cos(z/delta) + np.exp((-2*z)/delta)))
            
            # Note: negative added in front of arctan
            def vflow_phase(K, S_s, z=20, f=f_m2):
                D_h = K / S_s
                omega = 2*np.pi*(f/24/3600)
                delta = np.sqrt(2*D_h/omega)
                return np.arctan((np.exp(-z/delta)*np.sin(z/delta))/(1-np.exp(-z/delta)*np.cos(z/delta)))
            
            def residuals(props, amp, phase, depth, freq):
                K, S_s = props
                res_amp = amp*S_s - vflow_amp(K, S_s, depth, freq)
                res_phase = phase - vflow_phase(K, S_s, depth, freq)
                error = np.asarray([res_amp, res_phase])
                print(error)
                return error
            
            # least squares fitting wang
            fit =  least_squares(residuals, [0.01, 0.01], args=(amp, phase, scr_depth, f_m2), method='lm')
            
            # change units to m and s
            K = fit.x[0]
            Ss = fit.x[1]
            
            print(fit)
            
            print("-------------------------------------------------")
            if (fit.status > 0):
                print('Success:')   
                print("Hydraulic conductivity is: {:.3e} m/s".format(K))
                print("Specific storage is: {:.3e} 1/m".format(Ss))
                
                results.update({'K': K, 'Ss': Ss, 'Model': 'Wang', 'redidual': 'XXXX', 'screen_depth': scr_depth})
            else:
                print('Failed!')
        
        return results
    
    @staticmethod
    def Porosity():
        pass
        return
    
    @staticmethod
    def quantise(data, step):
        ''' Quantization of a signal '''
        return step*np.floor((data/step)+1/2)

    @staticmethod
    def harmonic_lsqr(tf, data, freqs):
        '''
        Inputs:
            tf      - time float. Should be an N x 1 numpy array.
            data    - estimated output. Should be an N x 1 numpy array.
            freqs   - frequencies to look for. Should be a numpy array.
        Outputs:
            alpha_est - estimated amplitudes of the sinusoids.
            phi_est - estimated phases of the sinusoids.
            error_variance - variance of the error. MSE of reconstructed signal compared to y.
            theta - parameters such that ||y - Phi*theta|| is
             minimized, where Phi is the matrix defined by
             freqs and tt that when multiplied by theta is a
             sum of sinusoids.
        '''

        N = data.shape[0]
        f = np.array(freqs)*2*np.pi
        num_freqs = len(f)
        # make sure that time vectors are relative
        # avoiding additional numerical errors
        tf = tf - np.floor(tf[0])
        # assemble the matrix
        Phi = np.empty((N, 2*num_freqs + 1))
        for j in range(num_freqs):
            Phi[:,2*j] = np.cos(f[j]*tf)
            Phi[:,2*j+1] = np.sin(f[j]*tf)
        # account for any DC offsets
        Phi[:,-1] = 1
        # solve the system of linear equations
        theta, residuals, rank, singular = np.linalg.lstsq(Phi, data, rcond=None)
        # calculate the error variance
        error_variance = residuals[0]/N
        # when data is short, 'singular value' is important!
        # 1 is perfect, larger than 10^5 or 10^6 there's a problem
        condnum = np.max(singular) / np.min(singular)
        # print('Conditioning number: {:,.0f}'.format(condnum))
        if (condnum > 1e6):
            warnings.warn('The least-squares solution is ill-conditioned (condition number is {:.1f})!'.format(condnum))
        # 	print(Phi)
        y_model = Phi@theta
        # the DC component
        dc_comp = theta[-1]
        # create complex coefficients
        hals_comp = theta[:-1:2]*1j + theta[1:-1:2]
        result = {'freq': freqs, 'complex': hals_comp, 'err_var': error_variance, 'cond_num': condnum, 'offset': dc_comp, 'y_model': y_model}

        return result

    @staticmethod
    def lin_window_ovrlp(tf, data, length=3, stopper=3, n_ovrlp=3):
        """
        Windowed linear detrend function with optional window overlap

        Parameters
        ----------
        time : N x 1 numpy array
            Sample times.
        y : N x 1 numpy array
            Sample values.
        length : int
            Window size in days
        stopper : int
            minimum number of samples within each window needed for detrending
        n_ovrlp : int
            number of window overlaps relative to the defined window length

        Returns
            -------
            y.detrend : array_like
                estimated amplitudes of the sinusoids.

        Notes
        -----
        A windowed linear detrend function with optional window overlap for pre-processing of non-uniformly sampled data.
        The reg_times array is extended by value of "length" in both directions to improve averaging and window overlap at boundaries. High overlap values in combination with high
        The "stopper" values will cause reducion in window numbers at time array boundaries.
        """

        x = np.array(tf).flatten()
        y = np.array(data).flatten()
        y_detr      = np.zeros(shape=(y.shape[0]))
        counter     = np.zeros(shape=(y.shape[0]))
        A = np.vstack([x, np.ones(len(x))]).T
        #num = 0 # counter to check how many windows are sampled
        interval    = length/(n_ovrlp+1) # step_size interval with overlap
        # create regular sampled array along t with step-size = interval.
        reg_times   = np.arange(x[0]-(x[1]-x[0])-length,x[-1]+length, interval)
        # extract indices for each interval
        idx         = [np.where((x > tt-(length/2)) & (x <= tt+(length/2)))[0] for tt in reg_times]
        # exclude samples without values (np.nan) from linear detrend
        idx         = [i[~np.isnan(y[i])] for i in idx]
        # only detrend intervals that meet the stopper criteria
        idx         = [x for x in idx if len(x) >= stopper]
        for i in idx:
            # find linear regression line for interval
            coe = np.linalg.lstsq(A[i],y[i],rcond=None)[0]
            # and subtract off data to detrend
            detrend = y[i] - (coe[0]*x[i] + coe[1])
            # add detrended values to detrend array
            np.add.at(y_detr,i,detrend)
            # count number of detrends per sample (depends on overlap)
            np.add.at(counter,i,1)
            
        # window gaps, marked by missing detrend are set to np.nan
        counter[counter==0] = np.nan
        # create final detrend array
        y_detrend = y_detr/counter
        if len(y_detrend[np.isnan(y_detrend)]) > 0:
            # replace nan-values assuming a mean of zero
            y_detrend[np.isnan(y_detrend)] = 0.0
            
        return y_detrend

    @staticmethod
    def fft_comp(tf, data):
        spd = 1/(tf[1] - tf[0])
        fft_N = len(tf)
        hanning = np.hanning(fft_N)
        # perform FFT
        fft_f = np.fft.fftfreq(int(fft_N), d=1/spd)[0:int(fft_N/2)]
        # FFT windowed for amplitudes
        fft_win   = np.fft.fft(hanning*data) # use signal with trend
        fft = 2*(fft_win/(fft_N/2))[0:int(fft_N/2)]
        # np.fft.fft default is a cosinus input. Thus for sinus the np.angle function returns a phase with a -np.pi shift.
        #fft_phs = fft_phs  + np.pi/2  # + np.pi/2 for a sinus signal as input
        #fft_phs = -(np.arctan(fft_win.real/fft_win.imag))
        result = {'freq': fft_f, 'complex': fft, 'dc_comp': np.abs(fft[0])}
        return result

    @staticmethod
    def regress_deconv(tf, GW, BP, ET=None, lag_h=24, et_method=None, fqs=None):
        et = True
        if ET is None and et_method is None:
            et = False
            et_method = 'hals'
        if fqs is None:
            fqs = np.array(list(const.const['_etfqs'].values()))
        # check that dataset is regularly sampled
        tmp = np.diff(tf)
        if (np.around(np.min(tmp), 6) != np.around(np.max(tmp), 6)):
            raise Exception("Error: Dataset must be regularly sampled!")
        if (len(tf) != len(GW) != len(BP)):
            raise Exception("Error: All input arrays must have the same length!")
        # decite if Earth tides are included or not
        if (et_method == 'hals'):
            print("DEBUG: PERFORM HALS")
            t  = tf
            # make time relative to avoid ET least squares errors
            dt = t[1] - t[0]
            spd = int(np.round(1/dt))
            # make the dataset relative
            dBP = np.diff(BP)/dt
            dWL = np.diff(GW)/dt
            # setup general parameters
            nlag = int((lag_h/24)*spd)
            n    = len(dBP)
            nn   = list(range(n))
            lags = list(range(nlag+1))
            nm = nlag+1
            # the regression matrix for barometric pressure
            v = np.zeros([n, nm])
            for i in range(nm):
                j = lags[i]
                k = np.arange(n-j)
                v[j+k, i] = -dBP[k]
            # consider ET
            if et:
                # prepare ET frequencies
                f = fqs
                NP = len(f)
                omega = 2.*np.pi*f
                # the regression matrix for Earth tides
                u1 = np.zeros([n, NP])
                u2 = u1.copy()
                for i in range(NP):
                    tau = omega[i]*t[nn]
                    u1[:,i] = np.cos(tau)
                    u2[:,i] = np.sin(tau)
                X = np.hstack([v, u1, u2])
            else:
                X = np.hstack([v])
            # perform regression ...
            Z = np.hstack([np.ones([n,1]), X])

            #%% perform least squares fitting
            # ----------------------------------------------
            # c  = np.linalg.lstsq(Z, dWL, rcond=None)[0]
            # ----------------------------------------------
            def brf_total(Z):
                #print(dir(Phi))
                def brf(x, *c):
                   # print(Phi)
                    return Z@c
                return brf
            c = 0.5*np.ones(Z.shape[1])
            c, covar = curve_fit(brf_total(Z), t, dWL, p0=c)

            #%% compute the singular values
            sgl = svdvals(Z)
            # 'singular value' is important: 1 is perfect,
            # larger than 10^5 or 10^6 there's a problem
            condnum = np.max(sgl) / np.min(sgl)
            # print('Conditioning number: {:,.0f}'.format(condnum))
            if (condnum > 1e6):
                warnings.warn('The least-squares estimation is ill-conditioned (condition number is {:.0f})!'.format(condnum))

            # ----------------------------------------------
            nc = len(c)
            # calculate the head corrections
            dWLc = dt*np.cumsum(np.dot(X, c[1:nc]))
            # deal with the missing values
            WLc = GW - np.concatenate([[0], dWLc])
            # set the corrected heads
            WLc += (np.nanmean(GW) - np.nanmean(WLc))

            # adjust for mean offset
            # trend  = c[0]
            lag_t = np.linspace(0, lag_h, int((lag_h/24)*spd) + 1, endpoint=True)
            # error propagation
            brf   = c[np.arange(1, nm+1)]
            brf_covar = covar[1:nm+1,1:nm+1]
            brf_var = np.diagonal(brf_covar)
            brf_stdev = np.sqrt(brf_var)
            cbrf   = np.cumsum(brf)
            # the error propagation for summation
            cbrf_var = np.zeros(brf_var.shape)
            for i in np.arange(0, nm):
            #    if (i == 4): break
                diag = np.diagonal(brf_covar[0:i+1, 0:i+1])
                triaglow = np.tril(brf_covar[0:i+1, 0:i+1], -1)
            #    print(covatl)
                cbrf_var[i] = np.sum(diag) + 2*np.sum(triaglow)
            cbrf_stdev = np.sqrt(cbrf_var)
            params = {'brf': {'lag': lag_t, 'irf': brf, 'irf_stdev': brf_stdev, 'crf': cbrf, 'crf_stdev': cbrf_stdev}}

            # consider ET if desired ...
            if et:
                k = np.arange(nm+1, NP+nm+1)
                # this is the result for the derivative WL/dt
                trf = np.array([a+(1j*b) for a,b in zip(c[k], c[NP+k])])
                # this is the correction for the frequency content in the WL
                # !!!!
                params.update({'erf': {'freq': fqs, 'comp': trf}})
            # return the method results
            return WLc, params

        # this method uses Earth tide time series
        elif(et_method == 'ts'):
            print("DEBUG: PERFORM TS")
            if et:
                if (ET is None):
                    raise Exception("Error: Please input valid Earth tide data!")
                if (len(tf) != len(ET)):
                    raise Exception("Error: Earth tide data must have the same length!")
            # start ...
            t  = tf
            # make time relative to avoid ET least squares errors
            dt = t[1] - t[0]
            # the data
            WL = GW

            #%% temporal derivatives
            spd = int(np.round(1/dt))
            #dt = 1./24.
            dBP = np.diff(BP)/dt
            dWL = np.diff(WL)/dt
            if et:
                dET = np.diff(ET)/dt

            #%% prepare matrices ...
            lag = range(int((lag_h/24)*spd) + 1)
            n   = len(dBP)
            nn  = range(n)
            nm = len(lag)
            V = np.zeros([n, nm])
            for i in range(nm):
                j = lag[i]
                k = np.arange(n-j)
                ### need negative?
                V[j+k, i] = -dBP[k]

            #%%
            if et:
                nm = len(lag)
                W = np.zeros([n, nm])
                for i in range(nm):
                    j = lag[i]
                    k = np.arange(n-j)
                    ### need negative?
                    W[j+k, i] = dET[k]
                XY = np.hstack([V, W])
            else:
                XY = V
            # stack the matrices
            Z = np.hstack([np.ones([n,1]), XY])

            #%% perform least squares fitting
            def brf_total(Z):
                #print(dir(Phi))
                def brf(x, *c):
                   # print(Phi)
                    return Z@c
                return brf
            c = 0.5*np.ones(Z.shape[1])
            c, covar = curve_fit(brf_total(Z), t, dWL, p0=c)

            #%% compute the singular values
            sgl = svdvals(Z)
            # 'singular value' is important: 1 is perfect,
            # larger than 10^5 or 10^6 there's a problem
            condnum = np.max(sgl) / np.min(sgl)
            # print('Conditioning number: {:,.0f}'.format(condnum))
            if (condnum > 1e6):
                warnings.warn('The least-squares estimation is ill-conditioned (condition number is {:.0f})!'.format(condnum))

            #%% determine the results
            nc = len(c)
            # calculate the head corrections
            dWLc = dt*np.cumsum(np.dot(XY, c[1:nc]))
            # deal with the missing values
            WLc = GW - np.concatenate([[0], dWLc])
            # set the corrected heads
            WLc += (np.nanmean(GW) - np.nanmean(WLc))

            #%% components
            # trend = c[0]
            lag_t = np.linspace(0, lag_h, int((lag_h/24)*spd) + 1, endpoint=True)
            # error propagation
            brf   = c[np.arange(1, nm+1)]
            brf_covar = covar[1:nm+1,1:nm+1]
            brf_var = np.diagonal(brf_covar)
            brf_stdev = np.sqrt(brf_var)
            cbrf   = np.cumsum(brf)
            # the error propagation for summation
            cbrf_var = np.zeros(brf_var.shape)
            for i in np.arange(0, nm):
            #    if (i == 4): break
                diag = np.diagonal(brf_covar[0:i+1, 0:i+1])
                triaglow = np.tril(brf_covar[0:i+1, 0:i+1], -1)
            #    print(covatl)
                cbrf_var[i] = np.sum(diag) + 2*np.sum(triaglow)
            cbrf_stdev = np.sqrt(cbrf_var)
            params = {'brf': {'lag': lag_t, 'irf': brf, 'irf_stdev': brf_stdev, 'crf': cbrf, 'crf_stdev': cbrf_stdev}}

            if et:
                erf = c[nm+1:2*nm+1]
                erf_covar = covar[nm+1:2*nm+1,nm+1:2*nm+1]
                erf_var = np.diagonal(erf_covar)
                erf_stdev = np.sqrt(erf_var)
                cerf = np.cumsum(erf)
                # the error propagation for summation
                cerf_var = np.zeros(brf_var.shape)
                for i in np.arange(0, nm):
                #    if (i == 4): break
                    diag = np.diagonal(erf_covar[0:i+1, 0:i+1])
                    triaglow = np.tril(erf_covar[0:i+1, 0:i+1], -1)
                #    print(covatl)
                    cerf_var[i] = np.sum(diag) + 2*np.sum(triaglow)
                cerf_stdev = np.sqrt(cerf_var)
                params.update({'erf': {'lag': lag_t, 'irf': erf, 'irf_stdev': erf_stdev, 'crf': cerf, 'crf_stdev': cerf_stdev}})

            return WLc, params
        else:
            raise Exception("Error: Please only use available Earth tide methods!")
