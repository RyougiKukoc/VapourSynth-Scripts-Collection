import vapoursynth as vs
from vapoursynth import core
from muvsfunc import SSIM_downsample


__version__ = "k.1.1.0"
_NNEDI3_CORE_ORDER = ('nnedi3vk', 'nnedi3cl', 'znedi3')
_NNEDI3_ALLOWED = {
    'nnedi3vk': {'field', 'dh', 'planes', 'nsize', 'nns', 'qual', 'etype', 'pscrn', 'device_index', 'list_device', 'num_streams'},
    'nnedi3cl': {'field', 'dh', 'planes', 'nsize', 'nns', 'qual', 'etype', 'pscrn', 'device', 'list_device', 'info'},
    'znedi3': {'field', 'dh', 'planes', 'nsize', 'nns', 'qual', 'etype', 'pscrn', 'opt', 'int16_prescreener', 'int16_predictor', 'exp', 'show_mask'},
}


def _normalize_nnedi3_core(preferred):
    if preferred is None:
        return None

    aliases = {
        'auto': None,
        'default': None,
        'nnedi3vk': 'nnedi3vk',
        'vk': 'nnedi3vk',
        'nnedi3cl': 'nnedi3cl',
        'cl': 'nnedi3cl',
        'znedi3': 'znedi3',
        'cpu': 'znedi3',
        'nnedi3': 'znedi3',
    }
    key = preferred.lower()
    if key not in aliases:
        raise ValueError(f'nnedi3_rpow2: unsupported nnedi3_core={preferred!r}')
    return aliases[key]


def _ordered_nnedi3_cores(preferred):
    preferred = _normalize_nnedi3_core(preferred)
    if preferred is None:
        return list(_NNEDI3_CORE_ORDER)
    return [preferred] + [name for name in _NNEDI3_CORE_ORDER if name != preferred]


def _call_nnedi3(clip, nnedi3_core=None, device=None, **kwargs):
    errors = []

    for name in _ordered_nnedi3_cores(nnedi3_core):
        try:
            if name == 'nnedi3vk':
                call_kwargs = {key: value for key, value in kwargs.items() if key in _NNEDI3_ALLOWED[name] and value is not None}
                if device is not None and 'device_index' not in call_kwargs:
                    call_kwargs['device_index'] = device
                return core.nnedi3vk.NNEDI3(clip, **call_kwargs)
            if name == 'nnedi3cl':
                call_kwargs = {key: value for key, value in kwargs.items() if key in _NNEDI3_ALLOWED[name] and value is not None}
                if device is not None and 'device' not in call_kwargs:
                    call_kwargs['device'] = device
                return core.nnedi3cl.NNEDI3CL(clip, **call_kwargs)

            call_kwargs = {key: value for key, value in kwargs.items() if key in _NNEDI3_ALLOWED[name] and value is not None}
            return core.znedi3.nnedi3(clip, **call_kwargs)
        except (AttributeError, RuntimeError, vs.Error) as exc:
            errors.append(f'{name}: {exc}')

    raise RuntimeError('nnedi3_rpow2: no nnedi3 backend could be initialized (' + '; '.join(dict.fromkeys(errors)) + ')')


def nnedi3_rpow2(clip, rfactor=2, width=None, height=None, correct_shift=True,
                 kernel="SSIM", nsize=0, nns=3, qual=None, etype=None, pscrn=None,
                 opt=True, int16_prescreener=None, int16_predictor=None, exp=None, upsizer=None, device=None, nnedi3_core=None):
    """nnedi3_rpow2 is for enlarging images by powers of 2.

    Args:
        rfactor (int): Image enlargement factor.
            Must be a power of 2 in the range [2 to 1024].
        correct_shift (bool): If False, the shift is not corrected.
            The correction is accomplished by using the subpixel
            cropping capability of fmtc's resizers.
        width (int): If correcting the image center shift by using the
            "correct_shift" parameter, width/height allow you to set a
            new output resolution.
        kernel (string): Sets the resizer used for correcting the image
            center shift that nnedi3_rpow2 introduces. This can be any of
            fmtc kernels, such as "cubic", "spline36", etc.
            spline36 is the default one.
        nnedi3_args (mixed): For help with nnedi3 args
            refert to nnedi3 documentation.
        upsizer (string): Legacy alias of nnedi3_core.
        nnedi3_core (string): Preferred implementation order anchor:
            nnedi3vk, nnedi3cl or znedi3.
    """

    if width is None:
        width = clip.width * rfactor
    if height is None:
        height = clip.height * rfactor
    hshift = 0.0
    vshift = -0.5
    pkdnnedi = dict(
        dh=True,
        nsize=nsize,
        nns=nns,
        qual=qual,
        etype=etype,
        pscrn=pscrn,
    )
    pkdchroma = dict(
        kernel=kernel, 
        sy=-0.5, 
        planes=[2, 3, 3]
    )

    tmp = 1
    times = 0
    while tmp < rfactor:
        tmp *= 2
        times += 1

    if rfactor < 2 or rfactor > 1024:
        raise ValueError("nnedi3_rpow2: rfactor must be between 2 and 1024.")

    if tmp != rfactor:
        raise ValueError("nnedi3_rpow2: rfactor must be a power of 2.")
    if nnedi3_core is None:
        nnedi3_core = upsizer
    pkdnnedi.update(
        opt=opt,
        int16_prescreener=int16_prescreener,
        int16_predictor=int16_predictor,
        exp=exp,
    )

    if correct_shift or clip.format.subsampling_h:
        if hasattr(core, "fmtc") is not True:
            raise RuntimeError("nnedi3_rpow2: fmtconv plugin is required.")

    last = clip

    for i in range(times):
        field = 1 if i == 0 else 0
        last = _call_nnedi3(last, nnedi3_core=nnedi3_core, device=device, field=field, **pkdnnedi)
        last = core.std.Transpose(last)
        if last.format.subsampling_w:
            # Apparently always using field=1 for the horizontal pass somehow
            # keeps luma/chroma alignment.
            field = 1
            hshift = hshift * 2 - 0.5
        else:
            hshift = -0.5
        last = _call_nnedi3(last, nnedi3_core=nnedi3_core, device=device, field=field, **pkdnnedi)
        last = core.std.Transpose(last)

    if clip.format.subsampling_h:
        if kernel == 'SSIM':
            pkdchroma['kernel'] = 'spline36'
        last = core.fmtc.resample(last, w=last.width, h=last.height, **pkdchroma)

    if correct_shift is True:
        if kernel == 'SSIM':
            last = SSIM_downsample(last, w=width, h=height, sx=hshift, sy=vshift, use_fmtc=True)
        else:
            last = core.fmtc.resample(last, w=width, h=height, kernel=kernel, sx=hshift, sy=vshift)

    if last.format.id != clip.format.id:
        last = core.fmtc.bitdepth(last, csp=clip.format.id)

    return last
