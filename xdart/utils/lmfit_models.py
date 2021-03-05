import numpy as np
from lmfit import Model
from lmfit.models import fwhm_expr, _validate_1d, update_param_vals
from lmfit.models import gaussian, lorentzian
from scipy.special import erf


def index_of(arr, val):
    """Return index of array nearest to a value."""
    if val < np.min(arr):
        return 0
    return np.abs(arr-val).argmin()


def _fwhm_expr_2D(model, parameter='sigma'):
    "return constraint expression for fwhm"
    return "%.7f*%s%s" % (model.fwhm_factor, model.prefix, parameter)


def guess_from_peak(model, y, x, negative, ampscale=1.0, sigscale=1.0, amp_area=True):
    """Estimate starting paramters 2D Peak fits

    The parameters are:
    - Amplitude (can be area or peak, see paramter:amp_area
    - Center
    - Sigma

    Parameters
    ----------
    model : instance of lmfit model class
        Must be a model of a 2D function with has parameters specified above

    y : 1D np.array
        y-data to which the model is fitted

    x : 1D np.array
        x-data to which the model is fitted

    negative: boolean
        Specify if the peak is an inverted peak

    ampscale: float
        Scale the amplitude estimated by this factor

    sigscale: float
        Scale the widths estimated by this factor

    amp_area: boolean
        Specify if the multiplicative coefficient of the function is amplitude or area

    Returns
    -------

    params object (see lmfit Model documentation for more details)

    """

    if x is None:
        return 1.0, 0.0, 1.0
    maxy, miny = max(y), min(y)
    maxx, minx = max(x), min(x)
    imaxy = index_of(y, maxy)

    #amp = (maxy - miny)
    amp = maxy - (y[0]+y[-1])/2.0
    cen = x[imaxy]
    sig = (maxx-minx)/6.0

    halfmax_vals = np.where(y > (maxy+miny)/2.0)[0]
    if negative:
        imaxy = index_of(y, miny)
        amp = -(maxy - miny)*2.0
        halfmax_vals = np.where(y < (maxy+miny)/2.0)[0]
    if len(halfmax_vals) > 2:
        sig = (x[halfmax_vals[-1]] - x[halfmax_vals[0]])/2.0
        cen = x[halfmax_vals].mean()
    amp = amp*ampscale
    if amp_area:
        amp *= sig*2.0
    sig = sig*sigscale

    pars = model.make_params(amplitude=amp, center=cen, sigma=sig)
    pars['%ssigma' % model.prefix].set(min=0.0)
    return pars


def update_param_hints(pars, **kwargs):
    """Update parameter hints with keyword arguments."""
    for pname, hints in kwargs.items():
        if pname in pars:
            for hint, val in hints.items():
                if val is not None:
                    setattr(pars[pname], hint, val)
    return pars


def guess_from_peak_2D(model, y, x, negative, ampscale=1.0, sigscale=1.0, amp_area=True):
    """Estimate starting paramters 2D Peak fits

    The parameters are:
    - Amplitude (can be area or peak, see paramter:amp_area
    - X Center
    - Y Center
    - X Sigma
    - Y Sigma


    Parameters
    ----------
    model : instance of lmfit model class
        Must be a model of a 2D function with has parameters specified above

    y : y-data to which the model is fitted
        Must be 1D flattened array

    x : 2D np.array (or 2 element list of 1D np.array)
        x-data - must be a 2D array, each of which has the same dimension as y

    negative: boolean
        Specify if the peak is an inverted peak

    ampscale: np.float
        Scale the amplitude estimated by this factor

    sigscale: np.float
        Scale the widths estimated by this factor

    amp_area: boolean
        Specify if the multiplicative coefficient of the 2D function is amplitude or area

    Returns
    -------

    params object (see lmfit Model documentation for more details)

    """
    if x is None:
        return 1.0, 0.0, 0.0, 1.0, 1.0
    x0 = x[0]
    x1 = x[1]

    maxy, miny = np.nanmax(y), np.nanmin(y)
    maxx0, minx0 = max(x0), min(x0)
    maxx1, minx1 = max(x1), min(x1)
    imaxy = index_of(y, maxy)

    # print('maxy, miny, maxx0, minx0, maxx1, minx1, imaxy', maxy, miny, maxx0, minx0, maxx1, minx1, imaxy)

    #amp = (maxy - miny)
    amp = maxy - (y[0] + y[-1])/2.0
    cen_x = x0[imaxy]
    cen_y = x1[imaxy]
    sig_x = (maxx0 - minx0)/6.0
    sig_y = (maxx1 - minx1)/6.0

    # print('amp, cen_x, cen_y, sig_x, sig_y', amp, cen_x, cen_y, sig_x, sig_y)

    halfmax_vals = np.where(y > (maxy+miny)/2.0)[0]
    # print('halfmax_vals', halfmax_vals)

    if negative:
        imaxy = index_of(y, miny)
        amp = -(maxy - miny)*2.0
        halfmax_vals = np.where(y < (maxy+miny)/2.0)[0]

    if len(halfmax_vals) > 2:
        sig_x = abs( (x0[halfmax_vals[-1]] - x0[halfmax_vals[0]]) / 2.0 )
        sig_y = abs( (x1[halfmax_vals[-1]] - x1[halfmax_vals[0]]) / 2.0 )

        cen_x = x0[halfmax_vals].mean()
        cen_y = x1[halfmax_vals].mean()

    amp = amp*ampscale
    if amp_area:
        amp *= sig_x * sig_y * 4.0
    sig_x = sig_x * sigscale
    sig_y = sig_y * sigscale

    # print('amp, cen_x, cen_y, sig_x, sig_y', amp, cen_x, cen_y, sig_x, sig_y)

    pars = model.make_params(amplitude=amp,
                             center_x=cen_x, center_y=cen_y,
                             sigma_x=sig_x,  sigma_y=sig_y)
    pars['%ssigma_x' % model.prefix].set(min=0.0)
    pars['%ssigma_y' % model.prefix].set(min=0.0)
    return pars


def lorentzian_squared(x, amplitude=1.0, center=0.0, sigma=1.0):
    """Lorentzian squared defined by amplitude
      amplitude*(1/(1 +((x[0] - x_center)/sigma_x)**2)**2

    The HWHM is related to the parameter :math:`\Gamma` by the relation:
      :math:`\kappa = \sqrt{\sqrt{2} - 1}\sigma`

    Parameters
    ----------
    x : 1D np.array
        input x data for which function value is calculated

    amplitude : np.float
        amplitude of the lorentzian-squared function

    center: np.float
        center of the lorentzian-squared function

    sigma : np.float
        sigma of the lorentzian-squared function

    Returns
    -------

    y : 1D np.array
        Returns the calculated value of the lorentzian-squared function
        for the given parameters

    """
    return amplitude * (1 / (1 + ((x - center) / sigma)**2) )**2


def pvoigt(x, amplitude=1.0, center=0.0, sigma=1.0, fraction=0.5):
    """Return a 1-dimensional pseudo-Voigt function.

    pvoigt(x, amplitude, center, sigma, fraction) =
       amplitude*(1-fraction)*gaussion(x, center, sigma_g) +
       amplitude*fraction*lorentzian(x, center, sigma)

    where sigma_g (the sigma for the Gaussian component) is

        sigma_g = sigma / sqrt(2*log(2)) ~= sigma / 1.17741

    so that the Gaussian and Lorentzian components have the
    same FWHM of 2*sigma.

    """
    sigma_g = sigma
    return ((1-fraction)*gaussian(x, amplitude, center, sigma_g) +
            fraction*lorentzian(x, amplitude, center, sigma))


def plane(x, intercept, slope_x, slope_y):
    """2D plane
    Function:
       :math:`f(x) = p_0 + p_1x + p_2y`

    Parameters
    ----------
    x : 2D np.array (or 2 element list of 1D np.array)
        x-data - must be a 2D array, each of which has the same dimension as y
        for which function value is calculated

    intercept : np.float
        intercept of the plane

    slope_x: np.float
        slope of plane along 1st dimension

    slope_y: np.float
        slope of plane along 2nd dimension

    Returns
    -------

    y : 2D np.array
        Returns the calculated value of the 2D plane for the given parameters

    """
    return intercept + slope_x * x[0] + slope_y * x[1]


def lor2_2D(x, amplitude=1.0, center_x=0.0, center_y=0.0, sigma_x=1.0, sigma_y=1.0):
    """2D Lorentzian squared defined by amplitude
    amplitude*(1/(1 +((x[0] - x_center)/sigma_x)**2 + ((x[1] - y_center)/sigma_y)**2))**2

    The HWHM is related to the parameter :math:`\Gamma` by the relation:
      :math:`\kappa = \sqrt{\sqrt{2} - 1}\Gamma`

    Parameters
    ----------
    x : 2D np.array (or 2 element list of 1D np.array)
        x-data - must be a 2D array, each of which has the same dimension as y
        for which function value is calculated

    amplitude : np.float
        amplitude of the 2D lorentzian-squared function

    center_x: np.float
        center of the lorentzian-squared function along the 1st dimension

    center_y: np.float
        center of the lorentzian-squared function along the 2nd dimension

    sigma_x : np.float
        sigma of the lorentzian-squared function along the 1st dimension

    sigma_y : np.float
        sigma of the lorentzian-squared function along the 2nd dimension

    Returns
    -------

    y : 2D np.array
        Returns the calculated value of the 2D lorentzian squared function
        for the given parameters

    """
    return amplitude * ( 1 / (1 + ((x[0] - center_x) / sigma_x)**2 +
                                  ((x[1] - center_y) / sigma_y)**2) )**2


def gauss_2D(x, amplitude=1.0, center_x=0.0, center_y=0.0, sigma_x=1.0, sigma_y=1.0):
    """2D Gaussian defined by amplitide
    out = amplitude * ( exp( -1.0 * (x[0] - center_x)**2 / (2 * sigma_x**2) +
                             -1.0 * (x[1] - center_y)**2 / (2 * sigma_y**2) ) )

    Parameters
    ----------
    x : 2D np.array (or 2 element list of 1D np.array)
        x-data - must be a 2D array, each of which has the same dimension as y
        for which function value is calculated

    amplitude : np.float
        amplitude of the 2D gaussian function

    center_x: np.float
        center of the 2D gaussian function along the 1st dimension

    center_y: np.float
        center of the 2D gaussian function along the 2nd dimension

    sigma_x : np.float
        sigma of the 2D gaussian function along the 1st dimension

    sigma_y : np.float
        sigma of the 2D gaussian function along the 2nd dimension

    Returns
    -------

    y : 2D np.array
        Returns the calculated value of the 2D gaussian function
        for the given parameters


    """
    return amplitude * ( np.exp( -1.0 * (x[0] - center_x)**2 / (2 * sigma_x**2) +
                                 -1.0 * (x[1] - center_y)**2 / (2 * sigma_y**2) ) )


def pvoigt_2D(x, amplitude=1.0, center_x=0.0, center_y=0.0,
        sigma_x=1.0, sigma_y=1.0, fraction=0.5):
    """Return a 2-dimensional pseudo-Voigt function.

    pvoigt(x, amplitude, center, sigma, fraction) =
       amplitude*(1-fraction)*gaussion(x, center, sigma_g) +
       amplitude*fraction*lorentzian(x, center, sigma)

    where sigma_g (the sigma for the Gaussian component) is

        sigma_g = sigma / sqrt(2*log(2)) ~= sigma / 1.17741

    so that the Gaussian and Lorentzian components have the
    same FWHM of 2*sigma.

    """
    sigma_x_g = sigma_x / 1.17741
    sigma_y_g = sigma_y / 1.17741
    return ((1-fraction)*gauss_2D(x, amplitude, center_x, center_y, sigma_x_g, sigma_y_g) +
            fraction*lor2_2D(x, amplitude, center_x, center_y, sigma_x, sigma_y))


def assymetric_rectangle(x, amplitude1=1.0, center1=0.0, sigma1=1.0,
                   amplitude2=1.0, center2=1.0, sigma2=1.0, form='linear'):
    """Return a rectangle function: step up, step down.

    (see step function)
    starts at 0.0, rises to amplitude (at center1 with width sigma1)
    then drops to 0.0 (at center2 with width sigma2) with form:
      'linear' (default) = ramp_up + ramp_down
      'atan', 'arctan'   = (amplitude1*atan(arg1) + amplitude2*atan(arg2))/pi
      'erf'              = (amplitude1*erf(arg1) + amplitude2*erf(arg2))/2.
      'logisitic'        = amplitude1*[1 - 1/(1 + exp(arg1))] + amplitude2*[1/2 - 1/(1+exp(arg2))]

    where arg1 =  (x - center1)/sigma1
    and   arg2 = -(x - center2)/sigma2

    """
    if abs(sigma1) < 1.e-13:
        sigma1 = 1.e-13
    if abs(sigma2) < 1.e-13:
        sigma2 = 1.e-13

    arg1 = (x - center1)/sigma1
    arg2 = (center2 - x)/sigma2
    if form == 'erf':
        out = 0.5*( amplitude1*(erf(arg1) + 1) + amplitude2*(erf(arg2) + 1))
    elif form.startswith('logi'):
        out = 0.5*( amplitude1*(1. - 1./(1. + np.exp(arg1))) + amplitude2(1. - 1./(1. + np.exp(arg2))) )
    elif form in ('atan', 'arctan'):
        out = (amplitude1*np.arctan(arg1) + amplitude2*np.arctan(arg2))/np.pi
    else:
        arg1[np.where(arg1 < 0)]  = 0.0
        arg1[np.where(arg1 > 1)]  = 1.0
        arg2[np.where(arg2 > 0)]  = 0.0
        arg2[np.where(arg2 < -1)] = -1.0
        out = amplitude1*arg1 + amplitude2*arg2
    return out

COMMON_DOC = """

Parameters
----------
independent_vars: list of strings to be set as variable names
missing: None, 'drop', or 'raise'
    None: Do not check for null or missing values.
    'drop': Drop null or missing observations in data.
        Use pandas.isnull if pandas is available; otherwise,
        silently fall back to numpy.isnan.
    'raise': Raise a (more helpful) exception when data contains null
        or missing values.
prefix: string to prepend to paramter names, needed to add two Models that
    have parameter names in common. None by default.
"""

class LorentzianSquaredModel(Model):
    """Model based on Lorentzian squared defined by amplitude
      amplitude*(1/(1 +((x[0] - x_center)/sigma_x)**2)**2

    The HWHM is related to the parameter :math:`\Gamma` by the relation:
      :math:`\kappa = \sqrt{\sqrt{2} - 1}\sigma`

    Parameters of Lorentzian Squared Function
    -----------------------------------------
    x : 1D np.array
        input x data for which function value is calculated

    amplitude : np.float
        amplitude of the lorentzian-squared function

    center: np.float
        center of the lorentzian-squared function

    sigma : np.float
        sigma of the lorentzian-squared function
    """
    __doc__ = lorentzian_squared.__doc__ + COMMON_DOC if lorentzian_squared.__doc__ else ""
    fwhm_factor = 2.0*np.sqrt(np.sqrt(2)-1)
    def __init__(self, *args, **kwargs):
        super(LorentzianSquaredModel, self).__init__(lorentzian_squared, *args, **kwargs)
        self.set_param_hint('sigma', min=0)
        self.set_param_hint('fwhm', expr=fwhm_expr(self))

    def guess(self, data, x=None, negative=False, **kwargs):
        pars = guess_from_peak(self, data, x, negative, ampscale=0.5, amp_area=False)
        return update_param_vals(pars, self.prefix, **kwargs)


class PlaneModel(Model):
    """Model based on 2D plane
    Function:
       :math:`f(x) = p_0 + p_1x + p_2y`

    Parameters of 2D Plane
    ----------------------
    x : 2D np.array (or 2 element list of 1D np.array)
        x-data - must be a 2D array, each of which has the same dimension as y
        for which function value is calculated

    intercept : np.float
        intercept of the plane

    slope_x: np.float
        slope of plane along 1st dimension

    slope_y: np.float
        slope of plane along 2nd dimension
    """
    __doc__ = plane.__doc__ + COMMON_DOC if plane.__doc__ else ""
    def __init__(self, *args, **kwargs):
        super(PlaneModel, self).__init__(plane, *args, **kwargs)

    def guess(self, data, x=None, **kwargs):
        sxval, syval, oval = 0., 0., 0.
        if x is not None:
            not_nan_inds = ~np.isnan(data)
            sxval, oval = np.polyfit(x[0][not_nan_inds], data[not_nan_inds], 1)
            syval, oval = np.polyfit(x[1][not_nan_inds], data[not_nan_inds], 1)
        pars = self.make_params(intercept=oval, slope_x=sxval, slope_y=syval)
        return update_param_vals(pars, self.prefix, **kwargs)


class LorentzianSquared2DModel(Model):
    """Model based on a 2D Lorentzian squared defined by amplitude
    amplitude*(1/(1 +((x[0] - x_center)/sigma_x)**2 + ((x[1] - y_center)/sigma_y)**2))**2

    The HWHM is related to the parameter :math:`\Gamma` by the relation:
      :math:`\kappa = \sqrt{\sqrt{2} - 1}\Gamma`

    Parameters of Lor2 Function
    ---------------------------
    x : 2D np.array (or 2 element list of 1D np.array)
        x-data - must be a 2D array, each of which has the same dimension as y
        for which function value is calculated

    amplitude : np.float
        amplitude of the 2D lorentzian-squared function

    center_x: np.float
        center of the lorentzian-squared function along the 1st dimension

    center_y: np.float
        center of the lorentzian-squared function along the 2nd dimension

    sigma_x : np.float
        sigma of the lorentzian-squared function along the 1st dimension

    sigma_y : np.float
        sigma of the lorentzian-squared function along the 2nd dimension

    """

    __doc__ = lor2_2D.__doc__ + COMMON_DOC if lor2_2D.__doc__ else ""
    fwhm_factor = 2.0*np.sqrt(np.sqrt(2)-1)
    def __init__(self, *args, **kwargs):
        super(LorentzianSquared2DModel, self).__init__(lor2_2D, *args, **kwargs)
        self.set_param_hint('sigma_x', min=0)
        self.set_param_hint('sigma_y', min=0)

        self.set_param_hint('fwhm_x', expr=_fwhm_expr_2D(self, parameter='sigma_x'))
        self.set_param_hint('fwhm_y', expr=_fwhm_expr_2D(self, parameter='sigma_y'))

    def guess(self, data, x=None, negative=False, **kwargs):
        pars = guess_from_peak_2D(self, data, x, negative, ampscale=1.25, amp_area=False)
        return update_param_vals(pars, self.prefix, **kwargs)


class Gaussian2DModel(Model):
    """A model based on a 2D Gaussian defined by amplitide
    out = amplitude * ( exp( -1.0 * (x[0] - center_x)**2 / (2 * sigma_x**2) +
                             -1.0 * (x[1] - center_y)**2 / (2 * sigma_y**2) ) )

    Parameters of Gaussian2D Function
    ---------------------------------
    x : 2D np.array (or 2 element list of 1D np.array)
        x-data - must be a 2D array, each of which has the same dimension as y
        for which function value is calculated

    amplitude : np.float
        amplitude of the 2D gaussian function

    center_x: np.float
        center of the 2D gaussian function along the 1st dimension

    center_y: np.float
        center of the 2D gaussian function along the 2nd dimension

    sigma_x : np.float
        sigma of the 2D gaussian function along the 1st dimension

    sigma_y : np.float
        sigma of the 2D gaussian function along the 2nd dimension
                             
    """

    __doc__ = gauss_2D.__doc__ + COMMON_DOC if gauss_2D.__doc__ else ""
    fwhm_factor = 2.354820
    def __init__(self, *args, **kwargs):
        super(Gaussian2DModel, self).__init__(gauss_2D, *args, **kwargs)
        self.set_param_hint('sigma_x', min=0)
        self.set_param_hint('sigma_y', min=0)
        self.set_param_hint('fwhm_x', expr=_fwhm_expr_2D(self, parameter='sigma_x'))
        self.set_param_hint('fwhm_y', expr=_fwhm_expr_2D(self, parameter='sigma_y'))

    def guess(self, data, x=None, negative=False, **kwargs):
        pars = guess_from_peak_2D(self, data, x, negative, ampscale=1., amp_area=False)
        return update_param_vals(pars, self.prefix, **kwargs)


class Pvoigt2DModel(Model):
    """Model based on a 2-dimensional pseudo-Voigt function.

    pvoigt(x, amplitude, center, sigma, fraction) =
       amplitude*(1-fraction)*gaussion(x, center, sigma_g) +
       amplitude*fraction*lorentzian(x, center, sigma)

    where sigma_g (the sigma for the Gaussian component) is

        sigma_g = sigma / sqrt(2*log(2)) ~= sigma / 1.17741

    so that the Gaussian and Lorentzian components have the
    same FWHM of 2*sigma.

    """
    __doc__ = pvoigt_2D.__doc__ + COMMON_DOC if pvoigt_2D.__doc__ else ""
    
    fwhm_factor = 2.0
    def __init__(self, *args, **kwargs):
        super(Pvoigt2DModel, self).__init__(pvoigt_2D, *args, **kwargs)
        self.set_param_hint('sigma_x', min=0)
        self.set_param_hint('sigma_y', min=0)
        self.set_param_hint('fwhm_x', expr=_fwhm_expr_2D(self, parameter='sigma_x'))
        self.set_param_hint('fwhm_y', expr=_fwhm_expr_2D(self, parameter='sigma_y'))

    def guess(self, data, x=None, negative=False, **kwargs):
        pars = guess_from_peak_2D(self, data, x, negative, ampscale=1., amp_area=False)
        return update_param_vals(pars, self.prefix, **kwargs)


class AssymetricRectangleModel(Model):
    """A model based on a Step-up and Step-down function, with five
    Parameters: ``amplitude`` (:math:`A`), ``center1`` (:math:`\mu_1`),
    ``center2`` (:math:`\mu_2`), `sigma1`` (:math:`\sigma_1`) and
    ``sigma2`` (:math:`\sigma_2`) and four choices for functional form
    (which is used for both the Step up and the Step down:

    - ``linear`` (the default)

    - ``atan`` or ``arctan`` for an arc-tangent function

    - ``erf`` for an error function

    - ``logistic`` for a logistic function (see http://en.wikipedia.org/wiki/Logistic_function).

    The function starts with a value 0, transitions to a value of
    :math:`A`, taking the value :math:`A/2` at :math:`\mu_1`, with :math:`\sigma_1`
    setting the characteristic width. The function then transitions again to
    the value :math:`A/2` at :math:`\mu_2`, with :math:`\sigma_2` setting the
    characteristic width. The forms are

    .. math::
        :nowrap:

        \begin{eqnarray*}
        &f(x; A, \mu, \sigma, {\mathrm{form={}'linear{}'}})   &= A \{ \min{[1, \max{(0, \alpha_1)}]} + \min{[-1, \max{(0,  \alpha_2)}]} \} \\
        &f(x; A, \mu, \sigma, {\mathrm{form={}'arctan{}'}})   &= A [\arctan{(\alpha_1)} + \arctan{(\alpha_2)}]/{\pi} \\
        &f(x; A, \mu, \sigma, {\mathrm{form={}'erf{}'}})      &= A [{\operatorname{erf}}(\alpha_1) + {\operatorname{erf}}(\alpha_2)]/2 \\
        &f(x; A, \mu, \sigma, {\mathrm{form={}'logistic{}'}}) &= A [1 - \frac{1}{1 + e^{\alpha_1}} - \frac{1}{1 +  e^{\alpha_2}} ]
        \end{eqnarray*}


    where :math:`\alpha_1  = (x - \mu_1)/{\sigma_1}` and
    :math:`\alpha_2  = -(x - \mu_2)/{\sigma_2}`.

    """

    def __init__(self, independent_vars=['x'], prefix='', missing=None,
                 name=None,  **kwargs):
        kwargs.update({'prefix': prefix, 'missing': missing,
                       'independent_vars': independent_vars})
        super(AssymetricRectangleModel, self).__init__(assymetric_rectangle, **kwargs)

        self.set_param_hint('center1')
        self.set_param_hint('center2')
        self.set_param_hint('midpoint',
                            expr='(%scenter1+%scenter2)/2.0' % (self.prefix,
                                                                self.prefix))

    def guess(self, data, x=None, negative=False, **kwargs):
        if x is None:
            return

        if negative:
            data *= -1

        ymin1, ymin2, ymax = min(data[:len(data)//4]), min(data[3*(len(data)//4):]), max(data)
        xmin1, xmin2, xmax = min(x), min(x), max(x)

        if negative:
            data  *= -1
            ymin1 *= -1
            ymin2 *= -1
            ymax  *= -1

        pars = self.make_params(amplitude1=(ymax-ymin1),
                                amplitude2=(ymax-ymin2),
                                center1=xmin1 +  (xmax-xmin1)//5,
                                center2=xmin1 +  (xmax-xmin1)//2)
        pars['%ssigma1' % self.prefix].set(value=abs(xmax-xmin1)/7.0, min=0.0)
        pars['%ssigma2' % self.prefix].set(value=abs(xmax-xmin2)/7.0, min=0.0)

        return update_param_vals(pars, self.prefix, **kwargs)


class PseudoVoigtModel(Model):
    r"""A model based on a pseudo-Voigt distribution function
    (see http://en.wikipedia.org/wiki/Voigt_profile#Pseudo-Voigt_Approximation),
    which is a weighted sum of a Gaussian and Lorentzian distribution functions
    that share values for ``amplitude`` (:math:`A`), ``center`` (:math:`\mu`)
    and full width at half maximum (and so have  constrained values of
    ``sigma`` (:math:`\sigma`).  A parameter ``fraction`` (:math:`\alpha`)
    controls the relative weight of the Gaussian and Lorentzian components,
    giving the full definition of

    .. math::

        f(x; A, \mu, \sigma, \alpha) = \frac{(1-\alpha)A}{\sigma_g\sqrt{2\pi}}
        e^{[{-{(x-\mu)^2}/{{2\sigma_g}^2}}]}
        + \frac{\alpha A}{\pi} \big[\frac{\sigma}{(x - \mu)^2 + \sigma^2}\big]

    where :math:`\sigma_g = {\sigma}/{\sqrt{2\ln{2}}}` so that the full width
    at half maximum of each component and of the sum is :math:`2\sigma`. The
    :meth:`guess` function always sets the starting value for ``fraction`` at 0.5.

    """

    fwhm_factor = 2.0

    def __init__(self, independent_vars=['x'], prefix='', missing=None,
                 name=None,  **kwargs):
        kwargs.update({'prefix': prefix, 'missing': missing,
                       'independent_vars': independent_vars})
        super(PseudoVoigtModel, self).__init__(pvoigt, **kwargs)
        self.set_param_hint('sigma', min=0)
        self.set_param_hint('fraction', value=0.5)
        self.set_param_hint('fwhm', expr=fwhm_expr(self))

    def guess(self, data, x=None, negative=False, **kwargs):
        pars = guess_from_peak(self, data, x, negative, ampscale=1.25)
        pars['%sfraction' % self.prefix].set(value=0.5)

        return update_param_vals(pars, self.prefix, **kwargs)
