import vapoursynth as vs
import mvsfunc as mvf
import havsfunc as haf
import functools
from vsrgtools import awarpsharp
from vsmasktools import ASobel

MODULE_NAME = 'vsTAAmbk'
_AA_BACKEND_EXCEPTIONS = (AttributeError, TypeError, RuntimeError, vs.Error)
_NNEDI3_CORE_ORDER = ('nnedi3vk', 'nnedi3cl', 'znedi3')
_EEDI3_CORE_ORDER = ('eedi3vk2', 'vszipcl', 'vszip')


def _normalize_aa_core(kind, name):
    if name is None:
        return None
    normalized = str(name).strip().lower().replace('-', '').replace('_', '')
    if normalized in ('', 'auto', 'default'):
        return None
    if kind == 'nnedi3':
        aliases = {
            'nnedi3vk': 'nnedi3vk',
            'vk': 'nnedi3vk',
            'nnedi3cl': 'nnedi3cl',
            'cl': 'nnedi3cl',
            'znedi3': 'znedi3',
            'cpu': 'znedi3',
        }
    else:
        aliases = {
            'eedi3vk2': 'eedi3vk2',
            'vk': 'eedi3vk2',
            'vk2': 'eedi3vk2',
            'vszipcl': 'vszipcl',
            'zipcl': 'vszipcl',
            'vszip': 'vszip',
            'zip': 'vszip',
        }
    if normalized not in aliases:
        raise ValueError(MODULE_NAME + f': unsupported {kind}_core={name!r}')
    return aliases[normalized]


def _ordered_aa_cores(order, preferred):
    names = list(order)
    if preferred is not None:
        names = [preferred] + [name for name in names if name != preferred]
    return names


def _filter_kwargs(kwargs, allowed):
    return {key: value for key, value in kwargs.items() if key in allowed and value is not None}


def _get_rgvs_namespace():
    try:
        return vs.core.rgvs
    except AttributeError:
        return vs.core.zsmooth


def _same_layout_integer_format_id(clip, bits):
    subsampling_w = 0 if clip.format.color_family == vs.GRAY else clip.format.subsampling_w
    subsampling_h = 0 if clip.format.color_family == vs.GRAY else clip.format.subsampling_h
    return vs.core.query_video_format(clip.format.color_family, vs.INTEGER, bits, subsampling_w, subsampling_h).id


class _NNEDI3Dispatcher:
    _allowed = {
        'nnedi3vk': {'field', 'dh', 'planes', 'nsize', 'nns', 'qual', 'etype', 'pscrn', 'device_index', 'list_device', 'num_streams'},
        'nnedi3cl': {'field', 'dh', 'planes', 'nsize', 'nns', 'qual', 'etype', 'pscrn', 'device', 'list_device', 'info'},
        'znedi3': {'field', 'dh', 'planes', 'nsize', 'nns', 'qual', 'etype', 'pscrn', 'opt', 'int16_prescreener', 'int16_predictor', 'exp', 'show_mask'},
    }

    def __init__(self, preferred=None, device=None):
        self.preferred = _normalize_aa_core('nnedi3', preferred)
        self.device = device
        self.selected = None

    def _call_backend(self, name, clip, kwargs):
        if name == 'nnedi3vk':
            backend = self.core.nnedi3vk.NNEDI3
            call_kwargs = _filter_kwargs(kwargs, self._allowed[name])
            if self.device is not None and 'device_index' not in call_kwargs:
                call_kwargs['device_index'] = self.device
        elif name == 'nnedi3cl':
            backend = self.core.nnedi3cl.NNEDI3CL
            call_kwargs = _filter_kwargs(kwargs, self._allowed[name])
            if self.device is not None and 'device' not in call_kwargs:
                call_kwargs['device'] = self.device
        else:
            backend = self.core.znedi3.nnedi3
            call_kwargs = _filter_kwargs(kwargs, self._allowed['znedi3'])
        return backend(clip, **call_kwargs)

    @property
    def core(self):
        return vs.core

    def __call__(self, clip, **kwargs):
        errors = []
        for name in _ordered_aa_cores(_NNEDI3_CORE_ORDER, self.preferred):
            if self.selected is not None and name != self.selected:
                continue
            try:
                result = self._call_backend(name, clip, kwargs)
                self.selected = name
                return result
            except _AA_BACKEND_EXCEPTIONS as exc:
                errors.append(f'{name}: {exc}')
                if self.selected == name:
                    self.selected = None
        for name in _ordered_aa_cores(_NNEDI3_CORE_ORDER, self.preferred):
            if self.selected is None or name == self.selected:
                continue
            try:
                result = self._call_backend(name, clip, kwargs)
                self.selected = name
                return result
            except _AA_BACKEND_EXCEPTIONS as exc:
                errors.append(f'{name}: {exc}')
        raise RuntimeError(MODULE_NAME + ': nnedi3 backend initialization failed: ' + '; '.join(dict.fromkeys(errors)))


class _EEDI3Dispatcher:
    _allowed = {
        'eedi3vk2': {
            'field', 'dh', 'planes', 'alpha', 'beta', 'gamma', 'nrad', 'mdis', 'hp', 'vcheck',
            'vthresh0', 'vthresh1', 'vthresh2', 'sclip', 'mclip', 'device_index', 'list_device', 'num_streams'
        },
        'vszipcl': {
            'field', 'dh', 'alpha', 'beta', 'gamma', 'nrad', 'mdis', 'hp', 'vcheck', 'vthresh0',
            'vthresh1', 'vthresh2', 'sclip', 'device_id', 'list_device', 'num_streams', 'tune'
        },
        'vszip': {
            'field', 'dh', 'alpha', 'beta', 'gamma', 'nrad', 'mdis', 'hp', 'vcheck', 'vthresh0',
            'vthresh1', 'vthresh2', 'sclip', 'mclip'
        },
    }

    def __init__(self, preferred=None, device=None):
        self.preferred = _normalize_aa_core('eedi3', preferred)
        self.device = device
        self.selected = None

    @property
    def core(self):
        return vs.core

    def _call_backend(self, name, clip, kwargs):
        if name == 'eedi3vk2':
            backend = self.core.eedi3vk2.EEDI3
            call_kwargs = _filter_kwargs(kwargs, self._allowed[name])
            if self.device is not None and 'device_index' not in call_kwargs:
                call_kwargs['device_index'] = self.device
        elif name == 'vszipcl':
            backend = self.core.vszipcl.EEDI3
            call_kwargs = _filter_kwargs(kwargs, self._allowed[name])
            if kwargs.get('mclip') is not None:
                raise vs.Error('EEDI3: vszipcl does not support mclip')
            if self.device is not None and 'device_id' not in call_kwargs:
                call_kwargs['device_id'] = self.device
        else:
            backend = self.core.vszip.EEDI3
            call_kwargs = _filter_kwargs(kwargs, self._allowed['vszip'])
        return backend(clip, **call_kwargs)

    def __call__(self, clip, **kwargs):
        errors = []
        for name in _ordered_aa_cores(_EEDI3_CORE_ORDER, self.preferred):
            if self.selected is not None and name != self.selected:
                continue
            try:
                result = self._call_backend(name, clip, kwargs)
                self.selected = name
                return result
            except _AA_BACKEND_EXCEPTIONS as exc:
                errors.append(f'{name}: {exc}')
                if self.selected == name:
                    self.selected = None
        for name in _ordered_aa_cores(_EEDI3_CORE_ORDER, self.preferred):
            if self.selected is None or name == self.selected:
                continue
            try:
                result = self._call_backend(name, clip, kwargs)
                self.selected = name
                return result
            except _AA_BACKEND_EXCEPTIONS as exc:
                errors.append(f'{name}: {exc}')
        raise RuntimeError(MODULE_NAME + ': eedi3 backend initialization failed: ' + '; '.join(dict.fromkeys(errors)))


class Clip:
    def __init__(self, clip):
        self.core = vs.core
        self.clip = clip
        if not isinstance(clip, vs.VideoNode):
            raise TypeError(MODULE_NAME + ': clip is invalid.')
        self.clip_width = clip.width
        self.clip_height = clip.height
        self.clip_bits = clip.format.bits_per_sample
        self.clip_color_family = clip.format.color_family
        self.clip_sample_type = clip.format.sample_type
        self.clip_id = clip.format.id
        self.clip_subsample_w = clip.format.subsampling_w
        self.clip_subsample_h = clip.format.subsampling_h
        self.clip_is_gray = True if clip.format.num_planes == 1 else False


class AAParent(Clip):
    def __init__(self, clip, strength=0.0, down8=False):
        super(AAParent, self).__init__(clip)
        self.aa_clip = self.clip
        self.dfactor = 1 - max(min(strength, 0.5), 0)
        self.dw = round(self.clip_width * self.dfactor / 4) * 4
        self.dh = round(self.clip_height * self.dfactor / 4) * 4
        self.upw4 = round(self.dw * 0.375) * 4
        self.uph4 = round(self.dh * 0.375) * 4
        self.down8 = down8
        self.process_depth = self.clip_bits
        if down8 is True:
            self.down_8()
        if self.dfactor != 1:
            self.aa_clip = self.resize(self.aa_clip, self.dw, self.dh, shift=0)
        if self.clip_color_family is vs.GRAY:
            if self.clip_sample_type is not vs.INTEGER:
                raise TypeError(MODULE_NAME + ': clip must be integer format.')
        else:
            raise TypeError(MODULE_NAME + ': clip must be GRAY family.')

    def resize(self, clip, w, h, shift):
        try:
            resized = self.core.resize.Spline36(clip, w, h, src_top=shift)
        except vs.Error:
            resized = self.core.fmtc.resample(clip, w, h, sy=shift)
            if resized.format.bits_per_sample != self.process_depth:
                mvf.Depth(resized, self.process_depth)
        return resized

    def down_8(self):
        self.process_depth = 8
        self.aa_clip = mvf.Depth(self.aa_clip, 8)

    def output(self, aaed):
        if self.process_depth != self.clip_bits:
            return mvf.LimitFilter(self.clip, mvf.Depth(aaed, self.clip_bits), thr=1.0, elast=2.0)
        else:
            return aaed


class AANnedi3(AAParent):
    def __init__(self, clip, strength=0, down8=False, **args):
        super(AANnedi3, self).__init__(clip, strength, down8)
        self.nnedi3_args = {
            'nsize': args.get('nsize', 3),
            'nns': args.get('nns', 1),
            'qual': args.get('qual', 2),
        }
        self.opencl = args.get('opencl', False)
        self.nnedi3 = _NNEDI3Dispatcher(args.get('nnedi3_core'), args.get('opencl_device', 0))

    def out(self):
        aaed = self.nnedi3(self.aa_clip, field=1, dh=True, **self.nnedi3_args)
        aaed = self.resize(aaed, self.clip_width, self.clip_height, -0.5)
        aaed = self.core.std.Transpose(aaed)
        aaed = self.nnedi3(aaed, field=1, dh=True, **self.nnedi3_args)
        aaed = self.resize(aaed, self.clip_height, self.clip_width, -0.5)
        aaed = self.core.std.Transpose(aaed)
        return self.output(aaed)


class AANnedi3SangNom(AANnedi3):
    def __init__(self, clip, strength=0, down8=False, **args):
        super(AANnedi3SangNom, self).__init__(clip, strength, down8, **args)
        self.aa = args.get('aa', 48)

    def out(self):
        aaed = self.nnedi3(self.aa_clip, field=1, dh=True, **self.nnedi3_args)
        aaed = self.resize(aaed, self.clip_width, self.uph4, shift=-0.5)
        aaed = self.core.std.Transpose(aaed)
        aaed = self.nnedi3(aaed, field=1, dh=True, **self.nnedi3_args)
        aaed = self.resize(aaed, self.uph4, self.upw4, shift=-0.5)
        aaed = self.core.sangnom.SangNom(aaed, aa=self.aa)
        aaed = self.core.std.Transpose(aaed)
        aaed = self.core.sangnom.SangNom(aaed, aa=self.aa)
        aaed = self.resize(aaed, self.clip_width, self.clip_height, shift=0)
        return self.output(aaed)


class AANnedi3UpscaleSangNom(AANnedi3SangNom):
    def __init__(self, clip, strength=0, down8=False, **args):
        super(AANnedi3UpscaleSangNom, self).__init__(clip, strength, down8, **args)
        self.nnedi3_args = {
            'nsize': args.get('nsize', 1),
            'nns': args.get('nns', 3),
            'qual': args.get('qual', 2),
        }


class AAEedi3(AAParent):
    def __init__(self, clip, strength=0, down8=False, **args):
        super(AAEedi3, self).__init__(clip, strength, down8)
        self.eedi3_args = {
            'alpha': args.get('alpha', 0.5),
            'beta': args.get('beta', 0.2),
            'gamma': args.get('gamma', 20),
            'nrad': args.get('nrad', 3),
            'mdis': args.get('mdis', 30),
        }

        self.opencl = args.get('opencl', False)
        self.eedi3 = _EEDI3Dispatcher(args.get('eedi3_core'), args.get('opencl_device', 0))

    '''
    def build_eedi3_mask(self, clip):
        eedi3_mask = self.core.nnedi3.nnedi3(clip, field=1, show_mask=True)
        eedi3_mask = self.core.std.Expr([eedi3_mask, clip], "x 254 > x y - 0 = not and 255 0 ?")
        eedi3_mask_turn = self.core.std.Transpose(eedi3_mask)
        if self.dfactor != 1:
            eedi3_mask_turn = self.core.resize.Bicubic(eedi3_mask_turn, self.clip_height, self.dw)
        return eedi3_mask, eedi3_mask_turn
    '''

    def out(self):
        aaed = self.eedi3(self.aa_clip, field=1, dh=True, **self.eedi3_args)
        aaed = self.resize(aaed, self.dw, self.clip_height, shift=-0.5)
        aaed = self.core.std.Transpose(aaed)
        aaed = self.eedi3(aaed, field=1, dh=True, **self.eedi3_args)
        aaed = self.resize(aaed, self.clip_height, self.clip_width, shift=-0.5)
        aaed = self.core.std.Transpose(aaed)
        return self.output(aaed)


class AAEedi3SangNom(AAEedi3):
    def __init__(self, clip, strength=0, down8=False, **args):
        super(AAEedi3SangNom, self).__init__(clip, strength, down8, **args)
        self.aa = args.get('aa', 48)

    '''
    def build_eedi3_mask(self, clip):
        eedi3_mask = self.core.nnedi3.nnedi3(clip, field=1, show_mask=True)
        eedi3_mask = self.core.std.Expr([eedi3_mask, clip], "x 254 > x y - 0 = not and 255 0 ?")
        eedi3_mask_turn = self.core.std.Transpose(eedi3_mask)
        eedi3_mask_turn = self.core.resize.Bicubic(eedi3_mask_turn, self.uph4, self.dw)
        return eedi3_mask, eedi3_mask_turn
    '''

    def out(self):
        aaed = self.eedi3(self.aa_clip, field=1, dh=True, **self.eedi3_args)
        aaed = self.resize(aaed, self.dw, self.uph4, shift=-0.5)
        aaed = self.core.std.Transpose(aaed)
        aaed = self.eedi3(aaed, field=1, dh=True, **self.eedi3_args)
        aaed = self.resize(aaed, self.uph4, self.upw4, shift=-0.5)
        aaed = self.core.sangnom.SangNom(aaed, aa=self.aa)
        aaed = self.core.std.Transpose(aaed)
        aaed = self.core.sangnom.SangNom(aaed, aa=self.aa)
        aaed = self.resize(aaed, self.clip_width, self.clip_height, shift=0)
        return self.output(aaed)


class AAEedi2(AAParent):
    def __init__(self, clip, strength=0, down8=False, **args):
        super(AAEedi2, self).__init__(clip, strength, down8)
        self.eedi2_args = {
            'mthresh': args.get('mthresh', 10),
            'lthresh': args.get('lthresh', 20),
            'vthresh': args.get('vthresh', 20),
            'maxd': args.get('maxd', 24),
            'nt': args.get('nt', 50),
        }

        self.cuda = args.get('cuda', False)
        self.cuda_faster = args.get('cuda_faster', False)
        if self.cuda is True:
            try:
                if self.cuda_faster:
                    self.eedi2 = self.core.eedi2cuda.AA2
                else:
                    self.eedi2 = self.core.eedi2cuda.EEDI2
                self.eedi2_args['num_streams'] = args.get('cuda_num_streams', 1)
                self.eedi2_args['device_id'] = args.get('cuda_device', -1)
            except AttributeError:
                self.eedi2 = self.core.eedi2.EEDI2
        else:
            self.eedi2 = self.core.eedi2.EEDI2

    def out(self):
        if self.cuda_faster:
            aaed = self.eedi2(self.aa_clip, 1, **self.eedi2_args)
        else:
            aaed = self.eedi2(self.aa_clip, 1, **self.eedi2_args)
            aaed = self.resize(aaed, self.dw, self.clip_height, shift=-0.5)
            aaed = self.core.std.Transpose(aaed)
            aaed = self.eedi2(aaed, 1, **self.eedi2_args)
            aaed = self.resize(aaed, self.clip_height, self.clip_width, shift=-0.5)
            aaed = self.core.std.Transpose(aaed)
        return self.output(aaed)


class AAEedi2SangNom(AAEedi2):
    def __init__(self, clip, strength=0, down8=False, **args):
        super(AAEedi2SangNom, self).__init__(clip, strength, down8, **args)
        self.aa = args.get('aa', 48)

    def out(self):
        aaed = self.eedi2(self.aa_clip, 1, **self.eedi2_args)
        aaed = self.resize(aaed, self.dw, self.uph4, shift=-0.5)
        aaed = self.core.std.Transpose(aaed)
        aaed = self.eedi2(aaed, 1, **self.eedi2_args)
        aaed = self.resize(aaed, self.uph4, self.upw4, shift=-0.5)
        aaed = self.core.sangnom.SangNom(aaed, aa=self.aa)
        aaed = self.core.std.Transpose(aaed)
        aaed = self.core.sangnom.SangNom(aaed, aa=self.aa)
        aaed = self.resize(aaed, self.clip_width, self.clip_height, shift=0)
        return self.output(aaed)


class AASpline64NRSangNom(AAParent):
    def __init__(self, clip, strength=0, down8=False, **args):
        super(AASpline64NRSangNom, self).__init__(clip, strength, down8)
        self.aa = args.get('aa', 48)

    def out(self):
        aa_spline64 = self.core.fmtc.resample(self.aa_clip, self.upw4, self.uph4, kernel='spline64')
        aa_spline64 = mvf.Depth(aa_spline64, self.process_depth)
        aa_gaussian = self.core.fmtc.resample(self.aa_clip, self.upw4, self.uph4, kernel='gaussian', a1=100)
        aa_gaussian = mvf.Depth(aa_gaussian, self.process_depth)
        aaed = _repair(aa_spline64, aa_gaussian, 1)
        aaed = self.core.sangnom.SangNom(aaed, aa=self.aa)
        aaed = self.core.std.Transpose(aaed)
        aaed = self.core.sangnom.SangNom(aaed, aa=self.aa)
        aaed = self.core.std.Transpose(aaed)
        aaed = self.resize(aaed, self.clip_width, self.clip_height, shift=0)
        return self.output(aaed)


class AASpline64SangNom(AAParent):
    def __init__(self, clip, strength=0, down8=False, **args):
        super(AASpline64SangNom, self).__init__(clip, strength, down8)
        self.aa = args.get('aa', 48)

    def out(self):
        aaed = self.core.fmtc.resample(self.aa_clip, self.clip_width, self.uph4, kernel="spline64")
        aaed = mvf.Depth(aaed, self.process_depth)
        aaed = self.core.sangnom.SangNom(aaed, aa=self.aa)
        aaed = self.core.std.Transpose(self.resize(aaed, self.clip_width, self.clip_height, 0))
        aaed = self.core.fmtc.resample(aaed, self.clip_height, self.upw4, kernel="spline64")
        aaed = mvf.Depth(aaed, self.process_depth)
        aaed = self.core.sangnom.SangNom(aaed, aa=self.aa)
        aaed = self.core.std.Transpose(self.resize(aaed, self.clip_height, self.clip_width, 0))
        return self.output(aaed)


class AAPointSangNom(AAParent):
    def __init__(self, clip, strength=0, down8=False, **args):
        super(AAPointSangNom, self).__init__(clip, 0, down8)
        self.aa = args.get('aa', 48)
        self.upw = self.clip_width * 2
        self.uph = self.clip_height * 2
        self.strength = strength  # Won't use this

    def out(self):
        aaed = self.core.resize.Point(self.aa_clip, self.upw, self.uph)
        aaed = self.core.sangnom.SangNom(aaed, aa=self.aa)
        aaed = self.core.std.Transpose(aaed)
        aaed = self.core.sangnom.SangNom(aaed, aa=self.aa)
        aaed = self.core.std.Transpose(aaed)
        aaed = self.resize(aaed, self.clip_width, self.clip_height, 0)
        return self.output(aaed)


def mask_sobel(mthr, opencl=False, opencl_device=-1, **kwargs):
    core = vs.core
    if opencl is True:
        try:
            canny = functools.partial(core.tcanny.TCannyCL, device=opencl_device)
        except AttributeError:
            canny = core.tcanny.TCanny
    else:
        canny = core.tcanny.TCanny
    mask_kwargs = {
        'sigma': kwargs.get('sigma', 1.0),
        't_h': kwargs.get('t_h', 8.0),
        't_l': kwargs.get('t_l', 1.0),
    }

    if canny.signature.find('gmmax') >= 0:
        mask_kwargs['gmmax'] = kwargs.get('gmmax', max(1, min(255, mthr)))
    else:
        mask_kwargs['scale'] = kwargs.get('scale', 255 / max(1, min(255, mthr)))

    return lambda clip: canny(clip, mode=1, op=2, **mask_kwargs)


def mask_prewitt(mthr, **kwargs):
    core = vs.core

    def wrapper(clip):
        eemask_1 = core.std.Convolution(clip, [1, 1, 0, 1, 0, -1, 0, -1, -1], divisor=1, saturate=False)
        eemask_2 = core.std.Convolution(clip, [1, 1, 1, 0, 0, 0, -1, -1, -1], divisor=1, saturate=False)
        eemask_3 = core.std.Convolution(clip, [1, 0, -1, 1, 0, -1, 1, 0, -1], divisor=1, saturate=False)
        eemask_4 = core.std.Convolution(clip, [0, -1, -1, 1, 0, -1, 1, 1, 0], divisor=1, saturate=False)
        eemask = core.std.Expr([eemask_1, eemask_2, eemask_3, eemask_4], 'x y max z max a max')
        eemask = _removegrain(core.std.Expr(eemask, 'x %d <= x 2 / x 1.4 pow ?' % mthr), 4).std.Inflate()
        return eemask

    return wrapper


def mask_canny_continuous(mthr, opencl=False, opencl_device=-1, **kwargs):
    core = vs.core
    if opencl is True:
        try:
            canny = functools.partial(core.tcanny.TCannyCL, device=opencl_device)
        except AttributeError:
            canny = core.tcanny.TCanny
    else:
        canny = core.tcanny.TCanny
    mask_kwargs = {
        'sigma': kwargs.get('sigma', 1.0),
        't_h': kwargs.get('t_h', 8.0),
        't_l': kwargs.get('t_l', 1.0),
    }
    return lambda clip: _removegrain(
        canny(clip, mode=1, **mask_kwargs).std.Expr('x %d <= x 2 / x 2 * ?' % mthr),
        20 if clip.width > 1100 else 11
    )


def mask_canny_binarized(mthr, opencl=False, opencl_device=-1, **kwargs):
    core = vs.core
    if opencl is True:
        try:
            canny = functools.partial(core.tcanny.TCannyCL, device=opencl_device)
        except AttributeError:
            canny = core.tcanny.TCanny
    else:
        canny = core.tcanny.TCanny
    mask_kwargs = {
        'sigma': kwargs.get('sigma', max(min(0.01772 * mthr + 0.4823, 5.0), 0.5)),
        't_h': kwargs.get('t_h', 8.0),
        't_l': kwargs.get('t_l', 1.0),
    }
    return lambda clip: canny(clip, mode=0, **mask_kwargs).std.Maximum()


def mask_tedge(mthr, **kwargs):
    """
    Mainly based on Avisynth's plugin TEMmod(type=2) (https://github.com/chikuzen/TEMmod)
    """
    core = vs.core
    mthr /= 5

    def wrapper(clip):
        # The Maximum value of these convolution is 21930, thus we have to store the result in 16bit clip
        fake16 = core.std.Expr(clip, 'x', _same_layout_integer_format_id(clip, 16))
        ix = core.std.Convolution(fake16, [12, -74, 0, 74, -12], saturate=False, mode='h')
        iy = core.std.Convolution(fake16, [-12, 74, 0, -74, 12], saturate=False, mode='v')
        mask = core.std.Expr([ix, iy], 'x x * y y * + 0.0001 * sqrt 255.0 158.1 / * 0.5 +', _same_layout_integer_format_id(clip, 8))
        mask = core.std.Expr(mask, 'x %f <= x 2 / x 16 * ?' % mthr)
        mask = _removegrain(core.std.Deflate(mask), 20 if clip.width > 1100 else 11)
        return mask

    return wrapper


def mask_robert(mthr, **kwargs):
    core = vs.core

    def wrapper(clip):
        m1 = core.std.Convolution(clip, [0, 0, 0, 0, -1, 0, 0, 0, 1], saturate=False)
        m2 = core.std.Convolution(clip, [0, 0, 0, 0, 0, -1, 0, 1, 0], saturate=False)
        mask = core.std.Expr([m1, m2], 'x y max').std.Expr('x %d < x 255 ?' % mthr).std.Inflate()
        return mask

    return wrapper


def mask_msharpen(mthr, **kwargs):
    core = vs.core
    mthr /= 5
    return lambda clip: core.msmoosh.MSharpen(clip, threshold=mthr, strength=0, mask=True)


def mask_lthresh(clip, mthrs, lthreshes, mask_kernel, inexpand, **kwargs):
    core = vs.core
    gray8 = mvf.Depth(clip, 8) if clip.format.bits_per_sample != 8 else clip
    gray8 = core.std.ShufflePlanes(gray8, 0, vs.GRAY) if clip.format.color_family != vs.GRAY else gray8
    mthrs = mthrs if isinstance(mthrs, (list, tuple)) else [mthrs]
    lthreshes = lthreshes if isinstance(lthreshes, (list, tuple)) else [lthreshes]
    inexpand = inexpand if isinstance(inexpand, (list, tuple)) and len(inexpand) >= 2 else [inexpand, 0]

    mask_kernels = [mask_kernel(mthr, **kwargs) for mthr in mthrs]
    masks = [kernel(gray8) for kernel in mask_kernels]
    mask = ((len(mthrs) - len(lthreshes) == 1) and functools.reduce(
        lambda x, y: core.std.Expr([x, y, gray8], 'z %d < x y ?' % lthreshes[masks.index(y) - 1]), masks)) or masks[0]
    mask = [mask] + [core.std.Maximum] * inexpand[0]
    mask = functools.reduce(lambda x, y: y(x), mask)
    mask = [mask] + [core.std.Minimum] * inexpand[1]
    mask = functools.reduce(lambda x, y: y(x), mask)

    bps = clip.format.bits_per_sample
    mask = (bps > 8 and core.std.Expr(mask, 'x %d *' % (((1 << clip.format.bits_per_sample) - 1) // 255),
                                      eval('vs.GRAY' + str(bps)))) or mask
    return lambda clip_a, clip_b, show=False: (show is False and core.std.MaskedMerge(clip_a, clip_b, mask)) or mask


def mask_fadetxt(clip, lthr=225, cthr=(2, 2), expand=2, fade_num=(5, 5), apply_range=None):
    core = vs.core
    if clip.format.color_family != vs.YUV:
        raise TypeError(MODULE_NAME + ': fadetxt mask: only yuv clips are supported.')
    w = clip.width
    h = clip.height
    bps = clip.format.bits_per_sample
    ceil = (1 << bps) - 1
    neutral = 1 << (bps - 1)
    frame_count = clip.num_frames

    yuv = [core.std.ShufflePlanes(clip, i, vs.GRAY) for i in range(clip.format.num_planes)]
    try:
        yuv444 = [core.resize.Bicubic(plane, w, h, src_left=0.25) if yuv.index(plane) > 0 else plane for plane in yuv]
    except vs.Error:
        yuv444 = [mvf.Depth(core.fmtc.resample(plane, w, h, sx=0.25), 8)
                  if yuv.index(plane) > 0 else plane for plane in yuv]
    cthr_u = cthr if not isinstance(cthr, (list, tuple)) else cthr[0]
    cthr_v = cthr if not isinstance(cthr, (list, tuple)) else cthr[1]
    expr = 'x %d > y %d - abs %d < and z %d - abs %d < and %d 0 ?' % (lthr, neutral, cthr_u, neutral, cthr_v, ceil)
    mask = core.std.Expr(yuv444, expr)
    mask = [mask] + [core.std.Maximum] * expand
    mask = functools.reduce(lambda x, y: y(x), mask)

    if fade_num != 0:
        def shift_backward(n, mask_clip, num):
            return mask_clip[frame_count - 1] if n + num > frame_count - 1 else mask_clip[n + num]

        def shift_forward(n, mask_clip, num):
            return mask_clip[0] if n - num < 0 else mask_clip[n - num]

        fade_in_num = fade_num if not isinstance(fade_num, (list, tuple)) else fade_num[0]
        fade_out_num = fade_num if not isinstance(fade_num, (list, tuple)) else fade_num[1]
        fade_in = core.std.FrameEval(mask, functools.partial(shift_backward, mask_clip=mask, num=fade_in_num))
        fade_out = core.std.FrameEval(mask, functools.partial(shift_forward, mask_clip=mask, num=fade_out_num))
        mask = core.std.Expr([mask, fade_in, fade_out], 'x y max z max')
        if apply_range is not None and isinstance(apply_range, (list, tuple)):
            try:
                blank = core.std.BlankClip(mask)
                if 0 in apply_range:
                    mask = mask[apply_range[0]:apply_range[1]] + blank[apply_range[1]:]
                elif frame_count in apply_range:
                    mask = blank[0:apply_range[0]] + mask[apply_range[0]:apply_range[1]]
                else:
                    mask = blank[0:apply_range[0]] + mask[apply_range[0]:apply_range[1]] + blank[apply_range[1]:]
            except vs.Error:
                raise ValueError(MODULE_NAME + ': incorrect apply range setting. Possibly end less than start')
            except IndexError:
                raise ValueError(MODULE_NAME + ': incorrect apply range setting. '
                                               'Apply range must be a tuple/list with 2 elements')
    return mask


def daa(clip, mode=-1, opencl=False, opencl_device=-1, nnedi3_core=None):
    core = vs.core
    nnedi3 = _NNEDI3Dispatcher(nnedi3_core, opencl_device)
    if mode == -1:
        nn = nnedi3(clip, field=3)
        nnt = nnedi3(core.std.Transpose(clip), field=3).std.Transpose()
        clph = core.std.Merge(core.std.SelectEvery(nn, cycle=2, offsets=0),
                              core.std.SelectEvery(nn, cycle=2, offsets=1))
        clpv = core.std.Merge(core.std.SelectEvery(nnt, cycle=2, offsets=0),
                              core.std.SelectEvery(nnt, cycle=2, offsets=1))
        clp = core.std.Merge(clph, clpv)
    elif mode == 1:
        nn = nnedi3(clip, field=3)
        clp = core.std.Merge(core.std.SelectEvery(nn, cycle=2, offsets=0),
                             core.std.SelectEvery(nn, cycle=2, offsets=1))
    elif mode == 2:
        nnt = nnedi3(core.std.Transpose(clip), field=3).std.Transpose()
        clp = core.std.Merge(core.std.SelectEvery(nnt, cycle=2, offsets=0),
                             core.std.SelectEvery(nnt, cycle=2, offsets=1))
    else:
        raise ValueError(MODULE_NAME + ': daa: at least one direction should be processed.')
    return clp


def _legacy_temporal_stabilize(clip, src, delta=3, pel=1, retain=0.6):
    core = vs.core
    clip_bits = clip.format.bits_per_sample
    src_bits = src.format.bits_per_sample
    if clip_bits != src_bits:
        raise ValueError(MODULE_NAME + ': temporal_stabilize: bits depth of clip and src mismatch.')
    if delta not in [1, 2, 3]:
        raise ValueError(MODULE_NAME + ': temporal_stabilize: delta (1~3) invalid.')

    diff = core.std.MakeDiff(src, clip)
    clip_super = core.mv.Super(clip, pel=pel)
    diff_super = core.mv.Super(diff, pel=pel, levels=1)

    backward_vectors = [core.mv.Analyse(clip_super, isb=True, delta=i + 1, overlap=8, blksize=16) for i in range(delta)]
    forward_vectors = [core.mv.Analyse(clip_super, isb=False, delta=i + 1, overlap=8, blksize=16) for i in range(delta)]
    vectors = [vector for vector_group in zip(backward_vectors, forward_vectors) for vector in vector_group]

    stabilize_func = {
        1: core.mv.Degrain1,
        2: core.mv.Degrain2,
        3: core.mv.Degrain3
    }
    diff_stabilized = stabilize_func[delta](diff, diff_super, *vectors)

    neutral = 1 << (clip_bits - 1)
    expr = 'x {neutral} - abs y {neutral} - abs < x y ?'.format(neutral=neutral)
    diff_stabilized_limited = core.std.Expr([diff, diff_stabilized], expr)
    diff_stabilized = core.std.Merge(diff_stabilized_limited, diff_stabilized, retain)
    clip_stabilized = core.std.MakeDiff(src, diff_stabilized)
    return clip_stabilized


def soothe(clip, src, keep=24):
    core = vs.core
    clip_bits = clip.format.bits_per_sample
    src_bits = src.format.bits_per_sample
    if clip_bits != src_bits:
        raise ValueError(MODULE_NAME + ': temporal_stabilize: bits depth of clip and src mismatch.')

    neutral = 1 << (clip_bits - 1)
    ceil = (1 << clip_bits) - 1
    multiple = ceil // 255
    const = 100 * multiple
    kp = keep * multiple

    diff = core.std.MakeDiff(src, clip)

    softener_candidates = [
        ('std', 'AverageFrames', dict(weights=[1, 1, 1], scenechange=32)),
        ('misc', 'AverageFrames', dict(weights=[1, 1, 1], scenechange=32)),
        ('focus2', 'TemporalSoften2', dict(radius=1, luma_threshold=255, chroma_threshold=255, scenechange=32, mode=2))
    ]
    softener = None
    for namespace, func, param in softener_candidates:
        if hasattr(core, namespace) and hasattr(getattr(core, namespace), func):
            softener = functools.partial(getattr(getattr(core, namespace), func), **param)
            break
    if softener is None:
        raise RuntimeError(MODULE_NAME + ': no available diff softener. you may need to update your Vapoursynth.')

    diff_soften = softener(diff)
    diff_soothed_expr = "x {neutral} - y {neutral} - * 0 < x {neutral} - {const} / {kp} * {neutral} + " \
                        "x {neutral} - abs y {neutral} - abs > " \
                        "x {kp} * y {const} {kp} - * + {const} / x ? ?".format(neutral=neutral, const=const, kp=kp)
    diff_soothed = core.std.Expr([diff, diff_soften], diff_soothed_expr)
    clip_soothed = core.std.MakeDiff(src, diff_soothed)

    return clip_soothed


def aa_cycle(clip, aa_class, cycle, *args, **kwargs):
    aaed = aa_class(clip, *args, **kwargs).out()
    return aaed if cycle <= 0 else aa_cycle(aaed, aa_class, cycle - 1, *args, **kwargs)


def _legacy_TAAmbk(clip, aatype=1, aatypeu=None, aatypev=None, preaa=0, strength=0.0, cycle=0, mtype=None, mclip=None,
           mthr=None, mlthresh=None, mpand=(0, 0), txtmask=0, txtfade=0, thin=0, dark=0.0, sharp=0,
           aarepair=0, postaa=None, src=None, stabilize=0, down8=True, showmask=0,
           opencl=False, opencl_device=-1, cuda=False, cuda_num_streams=1, cuda_device=-1, cuda_faster=False,
           **kwargs):
    core = vs.core

    aatypeu = aatype if aatypeu is None else aatypeu
    aatypev = aatype if aatypev is None else aatypev
    if mtype is None:
        mtype = 0 if preaa == 0 and True not in (aatype, aatypeu, aatypev) else 1
    if postaa is None:
        postaa = True if abs(sharp) > 70 or (0.4 < abs(sharp) < 1) else False
    if src is None:
        src = clip
    else:
        if clip.format.id != src.format.id:
            raise ValueError(MODULE_NAME + ': clip format and src format mismatch.')
        elif clip.width != src.width or clip.height != src.height:
            raise ValueError(MODULE_NAME + ': clip resolution and src resolution mismatch.')

    preaa_clip = clip if preaa == 0 else daa(clip, preaa, opencl, opencl_device, kwargs.get("nnedi3_core"))
    edge_enhanced_clip = (thin != 0 and core.warp.AWarpSharp2(preaa_clip, depth=int(thin)) or preaa_clip)
    edge_enhanced_clip = (dark != 0 and haf.Toon(edge_enhanced_clip, str=float(dark)) or edge_enhanced_clip)

    aa_kernel = {
        0: lambda clip, *args, **kwargs: type('', (), {'out': lambda: clip}),
        1: AAEedi2,
        2: AAEedi3,
        3: AANnedi3,
        4: AANnedi3UpscaleSangNom,
        5: AASpline64NRSangNom,
        6: AASpline64SangNom,
        -1: AAEedi2SangNom,
        -2: AAEedi3SangNom,
        -3: AANnedi3SangNom,
        'Eedi2': AAEedi2,
        'Eedi3': AAEedi3,
        'Nnedi3': AANnedi3,
        'Nnedi3UpscaleSangNom': AANnedi3UpscaleSangNom,
        'Spline64NrSangNom': AASpline64NRSangNom,
        'Spline64SangNom': AASpline64SangNom,
        'Eedi2SangNom': AAEedi2SangNom,
        'Eedi3SangNom': AAEedi3SangNom,
        'Nnedi3SangNom': AANnedi3SangNom,
        'PointSangNom': AAPointSangNom,
        'Unknown': lambda clip, *args, **kwargs: type('', (), {
            'out': lambda: exec('raise ValueError(MODULE_NAME + ": unknown aatype, aatypeu or aatypev")')}),
        'Custom': kwargs.get('aakernel', lambda clip, *args, **kwargs: type('', (), {
            'out': lambda: exec('raise RuntimeError(MODULE_NAME + ": custom aatype: aakernel must be set.")')})),
    }

    if clip.format.color_family is vs.YUV:
        yuv = [core.std.ShufflePlanes(edge_enhanced_clip, i, vs.GRAY) for i in range(clip.format.num_planes)]
        aatypes = [aatype, aatypeu, aatypev]
        aa_classes = [aa_kernel.get(aatype, aa_kernel['Unknown']) for aatype in aatypes]
        aa_clips = [aa_cycle(plane, aa_class, cycle, strength if yuv.index(plane) == 0 else 0, down8,
                             opencl=opencl, opencl_device=opencl_device, cuda=cuda,
                             cuda_num_streams=cuda_num_streams, cuda_device=cuda_device, cuda_faster=cuda_faster,
                             **kwargs) for plane, aa_class in zip(yuv, aa_classes)]
        aaed_clip = core.std.ShufflePlanes(aa_clips, [0, 0, 0], vs.YUV)
    elif clip.format.color_family is vs.GRAY:
        gray = edge_enhanced_clip
        aa_class = aa_kernel.get(aatype, aa_kernel['Unknown'])
        aaed_clip = aa_cycle(gray, aa_class, cycle, strength, down8,
                             opencl=opencl, opencl_device=opencl_device, cuda=cuda,
                             cuda_num_streams=cuda_num_streams, cuda_device=cuda_device, cuda_faster=cuda_faster,
                             **kwargs)
    else:
        raise ValueError(MODULE_NAME + ': Unsupported color family.')

    abs_sharp = abs(sharp)
    if sharp >= 1:
        sharped_clip = haf.LSFmod(aaed_clip, strength=int(abs_sharp), defaults='old', source=src)
    elif sharp > 0:
        per = int(40 * abs_sharp)
        matrix = [-1, -2, -1, -2, 52 - per, -2, -1, -2, -1]
        sharped_clip = core.std.Convolution(aaed_clip, matrix)
    elif sharp == 0:
        sharped_clip = aaed_clip
    elif sharp > -1:
        sharped_clip = haf.LSFmod(aaed_clip, strength=round(abs_sharp * 100), defaults='fast', source=src)
    elif sharp == -1:
        blured = _removegrain(aaed_clip, 20 if aaed_clip.width > 1100 else 11)
        diff = core.std.MakeDiff(aaed_clip, blured)
        diff = _repair(diff, core.std.MakeDiff(src, aaed_clip), mode=13)
        sharped_clip = core.std.MergeDiff(aaed_clip, diff)
    else:
        sharped_clip = aaed_clip

    postaa_clip = sharped_clip if postaa is False else soothe(sharped_clip, src, 24)
    repaired_clip = ((aarepair > 0 and _repair(src, postaa_clip, aarepair)) or
                     (aarepair < 0 and _repair(postaa_clip, src, -aarepair)) or postaa_clip)
    stabilized_clip = repaired_clip if stabilize == 0 else _legacy_temporal_stabilize(repaired_clip, src, stabilize)

    if mclip is not None:
        try:
            masked_clip = core.std.MaskedMerge(src, stabilized_clip, mclip, first_plane=True)
            masker = type('', (), {'__call__': lambda *args, **kwargs: mclip})()
        except vs.Error:
            raise RuntimeError(
                MODULE_NAME + ': Something wrong with your mclip. Maybe format, resolution or bit_depth mismatch.')
    else:
        # Use lambda for lazy evaluation
        mask_kernel = {
            0: lambda: lambda a, b, *args, **kwargs: b,
            1: lambda: mask_lthresh(clip, mthr, mlthresh, mask_sobel, mpand, opencl=opencl,
                                    opencl_device=opencl_device, **kwargs),
            2: lambda: mask_lthresh(clip, mthr, mlthresh, mask_robert, mpand, **kwargs),
            3: lambda: mask_lthresh(clip, mthr, mlthresh, mask_prewitt, mpand, **kwargs),
            4: lambda: mask_lthresh(clip, mthr, mlthresh, mask_tedge, mpand, **kwargs),
            5: lambda: mask_lthresh(clip, mthr, mlthresh, mask_canny_continuous, mpand, opencl=opencl,
                                    opencl_device=opencl_device, **kwargs),
            6: lambda: mask_lthresh(clip, mthr, mlthresh, mask_msharpen, mpand, **kwargs),
            'Sobel': lambda: mask_lthresh(clip, mthr, mlthresh, mask_sobel, mpand, opencl=opencl,
                                          opencl_device=opencl_device, **kwargs),
            'Canny': lambda: mask_lthresh(clip, mthr, mlthresh, mask_canny_binarized, mpand, opencl=opencl,
                                          opencl_device=opencl_device, **kwargs),
            'Prewitt': lambda: mask_lthresh(clip, mthr, mlthresh, mask_prewitt, mpand, **kwargs),
            'Robert': lambda: mask_lthresh(clip, mthr, mlthresh, mask_robert, mpand, **kwargs),
            'TEdge': lambda: mask_lthresh(clip, mthr, mlthresh, mask_tedge, mpand, **kwargs),
            'Canny_Old': lambda: mask_lthresh(clip, mthr, mlthresh, mask_canny_continuous, mpand, opencl=opencl,
                                              opencl_device=opencl_device, **kwargs),
            'MSharpen': lambda: mask_lthresh(clip, mthr, mlthresh, mask_msharpen, mpand, **kwargs),
            'Unknown': lambda: exec('raise ValueError(MODULE_NAME + ": unknown mtype")')
        }
        mtype = 5 if mtype is None else mtype
        mthr = (24,) if mthr is None else mthr
        masker = mask_kernel.get(mtype, mask_kernel['Unknown'])()
        masked_clip = masker(src, stabilized_clip)

    if txtmask > 0 and clip.format.color_family is not vs.GRAY:
        text_mask = mask_fadetxt(clip, lthr=txtmask, fade_num=txtfade)
        txt_protected_clip = core.std.MaskedMerge(masked_clip, src, text_mask, first_plane=True)
    else:
        text_mask = src
        txt_protected_clip = masked_clip

    final_output = ((showmask == -1 and text_mask) or
                    (showmask == 1 and masker(None, src, show=True)) or
                    (showmask == 2 and core.std.StackVertical([core.std.ShufflePlanes([masker(None, src, show=True),
                                                               core.std.BlankClip(src)], [0, 1, 2], vs.YUV), src])) or
                    (showmask == 3 and core.std.Interleave([core.std.ShufflePlanes([masker(None, src, show=True),
                                                           core.std.BlankClip(src)], [0, 1, 2], vs.YUV), src])) or
                    txt_protected_clip)
    return final_output


# === MVUTENSILS MERGED LAYER ===

_LEGACY_ABLUR_KERNELS: dict[int, tuple[list[int], int]] = {
    0: ([1, 1, 1, 1, 3, 3, 12, 3, 3, 1, 1, 1, 1], 32),
    1: ([1, 4, 6, 4, 1], 16),
}


def legacy_ablur(clip: vs.VideoNode, *, blur: int = 2, blur_type: int = 0, planes=None) -> vs.VideoNode:
    if blur < 0:
        raise ValueError("legacy_ablur: blur must be at least 0")
    if blur_type not in _LEGACY_ABLUR_KERNELS:
        raise ValueError("legacy_ablur: blur_type must be 0 or 1")
    matrix, divisor = _LEGACY_ABLUR_KERNELS[blur_type]
    out = clip
    for _ in range(blur):
        out = vs.core.std.Convolution(out, matrix=matrix, divisor=divisor, mode="h", planes=planes)
        out = vs.core.std.Convolution(out, matrix=matrix, divisor=divisor, mode="v", planes=planes)
    return out


def legacy_awarpsharp2(
    clip: vs.VideoNode,
    *,
    thresh: float = 128,
    blur: int = 2,
    blur_type: int = 0,
    depth: int = 32,
    mask_first_plane: bool | None = None,
    planes=None,
) -> vs.VideoNode:
    blur_fn = functools.partial(legacy_ablur, blur=blur, blur_type=blur_type)
    return awarpsharp(
        clip,
        mask=ASobel,
        thresh=thresh,
        blur=blur_fn,
        depth_h=depth,
        depth_v=depth,
        mask_first_plane=mask_first_plane,
        planes=planes,
    )


def _validate_mv_kernel(func_name: str, mv_kernel: str) -> None:
    if mv_kernel not in {"mvu", "mv"}:
        raise vs.Error(f"{func_name}: mv_kernel must be 'mvu' or 'mv'")


def _repair(clip, repair_clip, mode):
    return _get_rgvs_namespace().Repair(clip, repair_clip, mode=mode)


def _removegrain(clip, mode):
    return _get_rgvs_namespace().RemoveGrain(clip, mode=mode)


def _awarpsharp2(clip, blur=2, depth=32):
    return legacy_awarpsharp2(clip, blur=blur, depth=depth)


class _AASpline64NRSangNom_mvu(AAParent):
    def __init__(self, clip, strength=0, down8=False, **args):
        super(_AASpline64NRSangNom_mvu, self).__init__(clip, strength, down8)
        self.aa = args.get("aa", 48)

    def out(self):
        aa_spline64 = self.core.fmtc.resample(self.aa_clip, self.upw4, self.uph4, kernel="spline64")
        aa_spline64 = mvf.Depth(aa_spline64, self.process_depth)
        aa_gaussian = self.core.fmtc.resample(self.aa_clip, self.upw4, self.uph4, kernel="gaussian", a1=100)
        aa_gaussian = mvf.Depth(aa_gaussian, self.process_depth)
        aaed = _repair(aa_spline64, aa_gaussian, 1)
        aaed = self.core.sangnom.SangNom(aaed, aa=self.aa)
        aaed = self.core.std.Transpose(aaed)
        aaed = self.core.sangnom.SangNom(aaed, aa=self.aa)
        aaed = self.core.std.Transpose(aaed)
        aaed = self.resize(aaed, self.clip_width, self.clip_height, shift=0)
        return self.output(aaed)


def _temporal_stabilize_mvu(clip, src, delta=3, pel=1, retain=0.6):
    core = vs.core
    clip_bits = clip.format.bits_per_sample
    src_bits = src.format.bits_per_sample
    if clip_bits != src_bits:
        raise ValueError(MODULE_NAME + ": temporal_stabilize: bits depth of clip and src mismatch.")
    if delta not in [1, 2, 3]:
        raise ValueError(MODULE_NAME + ": temporal_stabilize: delta (1~3) invalid.")

    diff = core.std.MakeDiff(src, clip)
    clip_super = haf.super_clip(core, clip, blksize=16, overlap=8, pel=pel)
    diff_super = haf.super_clip(core, diff, blksize=16, overlap=8, pel=pel, levels=1)
    backward_vectors = [haf.analyse(core, clip_super, isb=True, delta=i + 1, overlap=8, blksize=16, truemotion=True) for i in range(delta)]
    forward_vectors = [haf.analyse(core, clip_super, isb=False, delta=i + 1, overlap=8, blksize=16, truemotion=True) for i in range(delta)]
    vectors = [vector for vector_group in zip(backward_vectors, forward_vectors) for vector in vector_group]
    diff_stabilized = haf.degrain(core, diff, diff_super, vectors, thsad=400)

    neutral = 1 << (clip_bits - 1)
    expr = "x {neutral} - abs y {neutral} - abs < x y ?".format(neutral=neutral)
    diff_stabilized_limited = core.std.Expr([diff, diff_stabilized], expr)
    diff_stabilized = core.std.Merge(diff_stabilized_limited, diff_stabilized, retain)
    return core.std.MakeDiff(src, diff_stabilized)


def _mask_prewitt_mvu(mthr, **kwargs):
    core = vs.core

    def wrapper(clip):
        eemask_1 = core.std.Convolution(clip, [1, 1, 0, 1, 0, -1, 0, -1, -1], divisor=1, saturate=False)
        eemask_2 = core.std.Convolution(clip, [1, 1, 1, 0, 0, 0, -1, -1, -1], divisor=1, saturate=False)
        eemask_3 = core.std.Convolution(clip, [1, 0, -1, 1, 0, -1, 1, 0, -1], divisor=1, saturate=False)
        eemask_4 = core.std.Convolution(clip, [0, -1, -1, 1, 0, -1, 1, 1, 0], divisor=1, saturate=False)
        eemask = core.std.Expr([eemask_1, eemask_2, eemask_3, eemask_4], "x y max z max a max")
        eemask = _removegrain(core.std.Expr(eemask, "x %d <= x 2 / x 1.4 pow ?" % mthr), 4).std.Inflate()
        return eemask

    return wrapper


def _mask_canny_continuous_mvu(mthr, opencl=False, opencl_device=-1, **kwargs):
    core = vs.core
    if opencl is True:
        try:
            canny = functools.partial(core.tcanny.TCannyCL, device=opencl_device)
        except AttributeError:
            canny = core.tcanny.TCanny
    else:
        canny = core.tcanny.TCanny
    mask_kwargs = {
        "sigma": kwargs.get("sigma", 1.0),
        "t_h": kwargs.get("t_h", 8.0),
        "t_l": kwargs.get("t_l", 1.0),
    }
    return lambda clip: _removegrain(canny(clip, mode=1, **mask_kwargs).std.Expr("x %d <= x 2 / x 2 * ?" % mthr), 20 if clip.width > 1100 else 11)


def _mask_tedge_mvu(mthr, **kwargs):
    core = vs.core
    mthr /= 5

    def wrapper(clip):
        fake16 = core.std.Expr(clip, "x", _same_layout_integer_format_id(clip, 16))
        ix = core.std.Convolution(fake16, [12, -74, 0, 74, -12], saturate=False, mode="h")
        iy = core.std.Convolution(fake16, [-12, 74, 0, -74, 12], saturate=False, mode="v")
        mask = core.std.Expr([ix, iy], "x x * y y * + 0.0001 * sqrt 255.0 158.1 / * 0.5 +", _same_layout_integer_format_id(clip, 8))
        mask = core.std.Expr(mask, "x %f <= x 2 / x 16 * ?" % mthr)
        mask = _removegrain(core.std.Deflate(mask), 20 if clip.width > 1100 else 11)
        return mask

    return wrapper


def _TAAmbk_mvu(clip, aatype=1, aatypeu=None, aatypev=None, preaa=0, strength=0.0, cycle=0, mtype=None, mclip=None,
                mthr=None, mlthresh=None, mpand=(0, 0), txtmask=0, txtfade=0, thin=0, dark=0.0, sharp=0,
                aarepair=0, postaa=None, src=None, stabilize=0, down8=True, showmask=0,
                opencl=False, opencl_device=-1, cuda=False, cuda_num_streams=1, cuda_device=-1, cuda_faster=False,
                **kwargs):
    core = vs.core

    aatypeu = aatype if aatypeu is None else aatypeu
    aatypev = aatype if aatypev is None else aatypev
    if mtype is None:
        mtype = 0 if preaa == 0 and True not in (aatype, aatypeu, aatypev) else 1
    if postaa is None:
        postaa = True if abs(sharp) > 70 or (0.4 < abs(sharp) < 1) else False
    if src is None:
        src = clip
    else:
        if clip.format.id != src.format.id:
            raise ValueError(MODULE_NAME + ": clip format and src format mismatch.")
        elif clip.width != src.width or clip.height != src.height:
            raise ValueError(MODULE_NAME + ": clip resolution and src resolution mismatch.")

    preaa_clip = clip if preaa == 0 else daa(clip, preaa, opencl, opencl_device, kwargs.get('nnedi3_core'))
    edge_enhanced_clip = (thin != 0 and _awarpsharp2(preaa_clip, depth=int(thin)) or preaa_clip)
    edge_enhanced_clip = (dark != 0 and haf.Toon(edge_enhanced_clip, str=float(dark)) or edge_enhanced_clip)

    aa_kernel = {
        0: lambda clip, *args, **kwargs: type("", (), {"out": lambda: clip}),
        1: AAEedi2,
        2: AAEedi3,
        3: AANnedi3,
        4: AANnedi3UpscaleSangNom,
        5: _AASpline64NRSangNom_mvu,
        6: AASpline64SangNom,
        -1: AAEedi2SangNom,
        -2: AAEedi3SangNom,
        -3: AANnedi3SangNom,
        "Eedi2": AAEedi2,
        "Eedi3": AAEedi3,
        "Nnedi3": AANnedi3,
        "Nnedi3UpscaleSangNom": AANnedi3UpscaleSangNom,
        "Spline64NrSangNom": _AASpline64NRSangNom_mvu,
        "Spline64SangNom": AASpline64SangNom,
        "Eedi2SangNom": AAEedi2SangNom,
        "Eedi3SangNom": AAEedi3SangNom,
        "Nnedi3SangNom": AANnedi3SangNom,
        "PointSangNom": AAPointSangNom,
        "Unknown": lambda clip, *args, **kwargs: type("", (), {"out": lambda: exec('raise ValueError(MODULE_NAME + ": unknown aatype, aatypeu or aatypev")')}),
        "Custom": kwargs.get("aakernel", lambda clip, *args, **kwargs: type("", (), {"out": lambda: exec('raise RuntimeError(MODULE_NAME + ": custom aatype: aakernel must be set.")')})),
    }

    if clip.format.color_family is vs.YUV:
        yuv = [core.std.ShufflePlanes(edge_enhanced_clip, i, vs.GRAY) for i in range(clip.format.num_planes)]
        aatypes = [aatype, aatypeu, aatypev]
        aa_classes = [aa_kernel.get(current_aatype, aa_kernel["Unknown"]) for current_aatype in aatypes]
        aa_clips = [aa_cycle(plane, aa_class, cycle, strength if yuv.index(plane) == 0 else 0, down8,
                             opencl=opencl, opencl_device=opencl_device, cuda=cuda,
                             cuda_num_streams=cuda_num_streams, cuda_device=cuda_device, cuda_faster=cuda_faster,
                             **kwargs) for plane, aa_class in zip(yuv, aa_classes)]
        aaed_clip = core.std.ShufflePlanes(aa_clips, [0, 0, 0], vs.YUV)
    elif clip.format.color_family is vs.GRAY:
        gray = edge_enhanced_clip
        aa_class = aa_kernel.get(aatype, aa_kernel["Unknown"])
        aaed_clip = aa_cycle(gray, aa_class, cycle, strength, down8,
                             opencl=opencl, opencl_device=opencl_device, cuda=cuda,
                             cuda_num_streams=cuda_num_streams, cuda_device=cuda_device, cuda_faster=cuda_faster,
                             **kwargs)
    else:
        raise ValueError(MODULE_NAME + ": Unsupported color family.")

    abs_sharp = abs(sharp)
    if sharp >= 1:
        sharped_clip = haf.LSFmod(aaed_clip, strength=int(abs_sharp), defaults="old", source=src)
    elif sharp > 0:
        per = int(40 * abs_sharp)
        matrix = [-1, -2, -1, -2, 52 - per, -2, -1, -2, -1]
        sharped_clip = core.std.Convolution(aaed_clip, matrix)
    elif sharp == 0:
        sharped_clip = aaed_clip
    elif sharp > -1:
        sharped_clip = haf.LSFmod(aaed_clip, strength=round(abs_sharp * 100), defaults="fast", source=src)
    elif sharp == -1:
        blured = _removegrain(aaed_clip, 20 if aaed_clip.width > 1100 else 11)
        diff = core.std.MakeDiff(aaed_clip, blured)
        diff = _repair(diff, core.std.MakeDiff(src, aaed_clip), 13)
        sharped_clip = core.std.MergeDiff(aaed_clip, diff)
    else:
        sharped_clip = aaed_clip

    postaa_clip = sharped_clip if postaa is False else soothe(sharped_clip, src, 24)
    repaired_clip = ((aarepair > 0 and _repair(src, postaa_clip, aarepair)) or
                     (aarepair < 0 and _repair(postaa_clip, src, -aarepair)) or postaa_clip)
    stabilized_clip = repaired_clip if stabilize == 0 else _temporal_stabilize_mvu(repaired_clip, src, stabilize)

    if mclip is not None:
        try:
            masked_clip = core.std.MaskedMerge(src, stabilized_clip, mclip, first_plane=True)
            masker = type("", (), {"__call__": lambda *args, **kwargs: mclip})()
        except vs.Error as exc:
            raise RuntimeError(MODULE_NAME + ": Something wrong with your mclip. Maybe format, resolution or bit_depth mismatch.") from exc
    else:
        mask_kernel = {
            0: lambda: lambda a, b, *args, **kwargs: b,
            1: lambda: mask_lthresh(clip, mthr, mlthresh, mask_sobel, mpand, opencl=opencl, opencl_device=opencl_device, **kwargs),
            2: lambda: mask_lthresh(clip, mthr, mlthresh, mask_robert, mpand, **kwargs),
            3: lambda: mask_lthresh(clip, mthr, mlthresh, _mask_prewitt_mvu, mpand, **kwargs),
            4: lambda: mask_lthresh(clip, mthr, mlthresh, _mask_tedge_mvu, mpand, **kwargs),
            5: lambda: mask_lthresh(clip, mthr, mlthresh, _mask_canny_continuous_mvu, mpand, opencl=opencl, opencl_device=opencl_device, **kwargs),
            6: lambda: mask_lthresh(clip, mthr, mlthresh, mask_msharpen, mpand, **kwargs),
            "Sobel": lambda: mask_lthresh(clip, mthr, mlthresh, mask_sobel, mpand, opencl=opencl, opencl_device=opencl_device, **kwargs),
            "Canny": lambda: mask_lthresh(clip, mthr, mlthresh, mask_canny_binarized, mpand, opencl=opencl, opencl_device=opencl_device, **kwargs),
            "Prewitt": lambda: mask_lthresh(clip, mthr, mlthresh, _mask_prewitt_mvu, mpand, **kwargs),
            "Robert": lambda: mask_lthresh(clip, mthr, mlthresh, mask_robert, mpand, **kwargs),
            "TEdge": lambda: mask_lthresh(clip, mthr, mlthresh, _mask_tedge_mvu, mpand, **kwargs),
            "Canny_Old": lambda: mask_lthresh(clip, mthr, mlthresh, _mask_canny_continuous_mvu, mpand, opencl=opencl, opencl_device=opencl_device, **kwargs),
            "MSharpen": lambda: mask_lthresh(clip, mthr, mlthresh, mask_msharpen, mpand, **kwargs),
            "Unknown": lambda: exec('raise ValueError(MODULE_NAME + ": unknown mtype")'),
        }
        mtype = 5 if mtype is None else mtype
        mthr = (24,) if mthr is None else mthr
        masker = mask_kernel.get(mtype, mask_kernel["Unknown"])()
        masked_clip = masker(src, stabilized_clip)

    if txtmask > 0 and clip.format.color_family is not vs.GRAY:
        text_mask = mask_fadetxt(clip, lthr=txtmask, fade_num=txtfade)
        txt_protected_clip = core.std.MaskedMerge(masked_clip, src, text_mask, first_plane=True)
    else:
        text_mask = src
        txt_protected_clip = masked_clip

    final_output = ((showmask == -1 and text_mask) or
                    (showmask == 1 and masker(None, src, show=True)) or
                    (showmask == 2 and core.std.StackVertical([core.std.ShufflePlanes([masker(None, src, show=True),
                                                               core.std.BlankClip(src)], [0, 1, 2], vs.YUV), src])) or
                    (showmask == 3 and core.std.Interleave([core.std.ShufflePlanes([masker(None, src, show=True),
                                                           core.std.BlankClip(src)], [0, 1, 2], vs.YUV), src])) or
                    txt_protected_clip)
    return final_output


def temporal_stabilize(clip, src, delta=3, pel=1, retain=0.6, mv_kernel="mvu"):
    _validate_mv_kernel("temporal_stabilize", mv_kernel)
    if mv_kernel == "mv":
        return _legacy_temporal_stabilize(clip, src, delta=delta, pel=pel, retain=retain)
    return _temporal_stabilize_mvu(clip, src, delta=delta, pel=pel, retain=retain)


def TAAmbk(clip, aatype=1, aatypeu=None, aatypev=None, preaa=0, strength=0.0, cycle=0, mtype=None, mclip=None,
           mthr=None, mlthresh=None, mpand=(0, 0), txtmask=0, txtfade=0, thin=0, dark=0.0, sharp=0,
           aarepair=0, postaa=None, src=None, stabilize=0, down8=True, showmask=0,
           opencl=False, opencl_device=-1, cuda=False, cuda_num_streams=1, cuda_device=-1, cuda_faster=False,
           mv_kernel="mvu", **kwargs):
    _validate_mv_kernel("TAAmbk", mv_kernel)
    if mv_kernel == "mv":
        return _legacy_TAAmbk(clip, aatype=aatype, aatypeu=aatypeu, aatypev=aatypev, preaa=preaa, strength=strength, cycle=cycle, mtype=mtype, mclip=mclip,
                              mthr=mthr, mlthresh=mlthresh, mpand=mpand, txtmask=txtmask, txtfade=txtfade, thin=thin, dark=dark, sharp=sharp, aarepair=aarepair,
                              postaa=postaa, src=src, stabilize=stabilize, down8=down8, showmask=showmask, opencl=opencl, opencl_device=opencl_device,
                              cuda=cuda, cuda_num_streams=cuda_num_streams, cuda_device=cuda_device, cuda_faster=cuda_faster, **kwargs)
    return _TAAmbk_mvu(clip, aatype=aatype, aatypeu=aatypeu, aatypev=aatypev, preaa=preaa, strength=strength, cycle=cycle, mtype=mtype, mclip=mclip,
                       mthr=mthr, mlthresh=mlthresh, mpand=mpand, txtmask=txtmask, txtfade=txtfade, thin=thin, dark=dark, sharp=sharp, aarepair=aarepair,
                       postaa=postaa, src=src, stabilize=stabilize, down8=down8, showmask=showmask, opencl=opencl, opencl_device=opencl_device,
                       cuda=cuda, cuda_num_streams=cuda_num_streams, cuda_device=cuda_device, cuda_faster=cuda_faster, **kwargs)
