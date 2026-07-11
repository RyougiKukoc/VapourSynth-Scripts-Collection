# Thanks HQdering DeHalo_alpha YAHR, Write by saya E-mail:sayaonee@gmail.com
# v1.1.00 : modify Sdering_mod(2016/02/15)
# v1.0.00 : first stable version(2016/02/10)
import vapoursynth as vs
from vapoursynth import core
from havsfunc import MinBlur


### Edge-Detection modes ###
def edge_detect(clip: vs.VideoNode, mode="sobel", thY1=0, thY2=255, thC1=0, thC2=0) -> vs.VideoNode:
    # constant values for bit_depth adaptive
    sBitP = clip.format.bits_per_sample
    black = 0
    white = (1 << sBitP) - 1
    mode = mode.lower()

    # process chroma ?
    if thC1 == 0 and thC2 == 0:
        clp = core.std.ShufflePlanes(clip, 0, vs.GRAY)
        thY1 = round(thY1 / 255 * white)
        thY2 = round(thY2 / 255 * white)
        GRAY = True
    else:
        clp = clip
        thY1 = round(thY1 / 255 * white)
        thY2 = round(thY2 / 255 * white)
        thC1 = round(thC1 / 255 * white)
        thC2 = round(thC2 / 255 * white)
        GRAY = False
    
    # process
    # -- Sobel -- #
    if mode == "sobel":
        edge = clp.std.Convolution([0, -1, 0, -1, 0, 1, 0, 1, 0], saturate=False)
        exp = f"x {thY1} < {black} x ? {thY2} > {white} x ?"
        if not GRAY:
            expC = f"x {thC1} < {black} x ? {thC2} > {white} x ?"
            edge = core.std.Expr(edge, [exp, expC])
        else:
            edge = core.std.Expr(edge, [exp])
    # -- Roberts -- #
    elif mode == "roberts":
        edge = clp.std.Convolution([0, 0, 0, 0, 2, -1, 0, -1, 0], saturate=False)
        exp = f"x {thY1} < {black} x ? {thY2} > {white} x ?"
        if not GRAY:
            expC = f"x {thC1} < {black} x ? {thC2} > {white} x ?"
            edge = core.std.Expr(edge, [exp,expC])
        else:
            edge = core.std.Expr(edge, [exp])
    # -- Laplace -- #
    elif mode == "laplace":
        edge = clp.std.Convolution([1, 1, 1, 1, -8, 1, 1, 1, 1])
        exp = f"x {thY1} < {black} x ? {thY2} > {white} x ?"
        if not GRAY:
            expC = f"x {thC1} < {black} x ? {thC2} > {white} x ?"
            edge = core.std.Expr(edge, [exp,expC])
        else:
            edge = core.std.Expr(edge, [exp])
    # -- Prewitt -- #
    elif mode == "prewitt":
        edgemask1 = clp.std.Convolution([1, 1, 0, 1, 0, -1, 0, -1, -1], divisor=1, saturate=False, planes=0)
        edgemask2 = clp.std.Convolution([1, 1, 1, 0, 0, 0, -1, -1, -1], divisor=1, saturate=False, planes=0)
        edgemask3 = clp.std.Convolution([1, 0, -1, 1, 0, -1, 1, 0, -1], divisor=1, saturate=False, planes=0)
        edgemask4 = clp.std.Convolution([0, -1, -1, 1, 0, -1, 1, 1, 0], divisor=1, saturate=False, planes=0)
        exp = "x y max z max a max"
        exp2 = f"x {thY1} < {black} x ? {thY2} > {white} x ?"
        if not GRAY:
            expC = "x y max z max a max"
            exp2C = f"x {thC1} < {black} x ? {thC2} > {white} x ?"
            edge = core.std.Expr([edgemask1, edgemask2, edgemask3, edgemask4], [exp, expC])
            edge = core.std.Expr(edge, [exp2, exp2C])
        else:
            edge = core.std.Expr([edgemask1, edgemask2, edgemask3, edgemask4], [exp])
            edge = core.std.Expr(edge, [exp2])
    # -- min/max -- #
    elif mode == "min/max":
        maxi = core.std.Maximum(clp)
        mini = core.std.Minimum(clp)
        exp = "x y -"
        exp2 = f"x {thY1} < {black} x ? {thY2} > {white} x ?"
        if not GRAY:
            expC = "x y -"
            exp2C = f"x {thC1} < {black} x ? {thC2} > {white} x ?"
            edge = core.std.Expr([maxi, mini], [exp, expC])
            edge = core.std.Expr(edge, [exp2, exp2C])
        else:
            edge = core.std.Expr([maxi, mini], [exp])
            edge = core.std.Expr(edge, [exp2])
    # -- hprewitt -- #
    elif mode == "hprewitt":
        edge1 = clp.std.Convolution([1, 2, 1, 0, 0, 0, -1, -2, -1], divisor=1, saturate=False)
        edge2 = clp.std.Convolution([1, 0, -1, 2, 0, -2, 1, 0, -1], divisor=1, saturate=False)
        exp = "x y max"
        exp2 = f"x {thY1} < {black} x ? {thY2} > {white} x ?"
        if not GRAY:
            expC = "x y max"
            exp2C = f"x {thC1} < {black} x ? {thC2} > {white} x ?"
            edge = core.std.Expr([edge1, edge2], [exp, expC])
            edge = core.std.Expr(edge, [exp2, exp2C])
        else:
            edge = core.std.Expr([edge1, edge2], [exp])
            edge = core.std.Expr(edge, [exp2])
    else:
        raise ValueError("edge_detection: \"mode\" invalid !")
    return edge


### Internal functions ###
def Depth(clip: vs.VideoNode, depth=None) -> vs.VideoNode:
    sbitPS = clip.format.bits_per_sample
    if sbitPS == depth:
        return clip
    else:
        return clip.fmtc.bitdepth(bits=depth, flt=0, dmode=3)


def mask_process(msk: vs.VideoNode, pro1=None, pro1_diff=None, prepro2=None, pro2=None, pro2_diff=None,
                 maskpro1=None, maskpro2=None) -> vs.VideoNode:
    sBitP = msk.format.bits_per_sample
    if pro1 is None:
        pro1 = MinBlur(msk, 2).rgvs.RemoveGrain(11)
    if pro1_diff is None:
        pro1_diff = core.std.MakeDiff(msk, pro1)
    if prepro2 is None:
        msk_8 = Depth(msk, 8)
        prepro2 = core.warp.AWarpSharp2(msk_8, depth=32, blur=2, thresh=128)
        prepro2 = Depth(prepro2, sBitP)
    if pro2 is None:
        pro2 = MinBlur(prepro2, 2, [0]).rgvs.RemoveGrain(11)
    if pro2_diff is None:
        pro2_diff = core.std.MakeDiff(prepro2, pro2)
    if maskpro1 is None:
        maskpro1 = core.rgvs.Repair(pro1_diff, pro2_diff, 13)
    if maskpro2 is None:
        maskpro2 = core.std.MakeDiff(pro1_diff, maskpro1)
    maskpro3 = core.std.MakeDiff(msk, maskpro2)
    return maskpro3


def dering_process(clp: vs.VideoNode, strength1=None, strength2=None, mode=None, dering_line_mask1=None, 
                   ps1mask=None, thickmask=None, dering_line_mask2=None) -> vs.VideoNode:
    def chkexpr(expr: str) -> list:
        if clp.format.num_planes > 1:
            return [expr, ""]
        else:
            return [expr]
    
    sBitP = clp.format.bits_per_sample
    white = (1 << sBitP) - 1

    # default settings
    if mode is None:
        mode = 1
    else:
        if not isinstance(mode, int):
            raise TypeError('\"mode\" invalid! [1-3]')
    
    # preset for strength
    pnum = mode - 1
    if strength1 is None: strength1 = [100, 125, 255][pnum]
    if strength2 is None: strength2 = [0.6, 1.0,   0][pnum]
    strength1 = round(strength1 / 255 * white)
    x = round((clp.width / 4) * 4)
    y = round((clp.height / 4) * 4)
    x2 = int(x / 2)
    y2 = int(y / 2)
    xs = int(x * 3 / 2)
    ys = int(y * 3 / 2)
    
    # mask
    if dering_line_mask1 is None:
        dering_line_mask1 = edge_detect(clp, "sobel", 4, 255, 0, 0)
    if ps1mask is None:
        ps1mask = dering_line_mask1.std.Levels(0, round(90 / 255 * white), 3.3, 0, white).rgvs.RemoveGrain(11)
    if thickmask is None:
        thickmask = dering_line_mask1.std.Inflate().std.Inflate().std.Inflate()
        thickmask = thickmask.std.Levels(0, round(90 / 255 * white), 3.3, 0, white).rgvs.RemoveGrain(11)
        thickmask = thickmask.std.Inflate().std.Inflate().std.Levels(0, white, 3.3, 0, white)
        thickmask = thickmask.std.Inflate().std.Inflate()
    if dering_line_mask2 is None:
        ps1mask_ivt = ps1mask.std.Invert()
        dering_line_mask2 = core.std.Expr([ps1mask_ivt, thickmask], [f"x y * {white} /"])

    ps1 = core.std.MaskedMerge(
        clipa = clp,
        clipb = clp.rgvs.RemoveGrain(20),
        mask = dering_line_mask2.std.Levels(round(60 / 255 * white), round(140 / 255 * white), 3.0, 0, strength1),
        first_plane = True
    )
    
    # dehalo
    halo = ps1.resize.Bicubic(width=x2, height=y2).resize.Bicubic(
        width = x,
        height = y, 
        filter_param_a = 1, 
        filter_param_b = 0, 
        filter_param_a_uv = 1, 
        filter_param_b_uv = 0
    )
    halo_mask1 = core.std.Expr([ps1.std.Maximum(), clp.std.Minimum()], chkexpr("x y -"))
    halotomask = core.std.Expr([halo.std.Maximum(), halo.std.Minimum()], chkexpr("x y -"))
    num1 = round(0.001 / 255 * white)
    num2 = round(50 / 255 * white)
    num3 = white + 1
    num4 = round(0.5 / 255 * white)
    num5 = round(512 / 255 * white)
    halotomask2 = core.std.Expr(
        clips = [halotomask, halo_mask1], 
        expr = [f"y x - y {num1} + / {white} * {num2} - y {num3} + {num5} / {num4} + *"]
    )
    pshalo = core.std.MaskedMerge(halo, ps1, halotomask2, [0], True)
    pshalo2 = core.resize.Lanczos(ps1, xs, ys, filter_param_a=4, resample_filter_uv="spline36")
    pshalo2 = core.std.Expr([pshalo.std.Maximum().resize.Bicubic(xs, ys), pshalo2], chkexpr("x y min"))
    pshalo2 = core.std.Expr([pshalo.std.Minimum().resize.Bicubic(xs, ys), pshalo2], chkexpr("x y max"))
    pshalo2 = core.resize.Lanczos(pshalo2, x, y, filter_param_a=4, resample_filter_uv="spline36")
    if mode != 3:
        ps2 = core.std.Expr([ps1, pshalo2], chkexpr(f"x y < x x y - {strength2} * - x x y - 1 * - ?"))
    else:
        ps2 = ps1
    return ps2


def dering_process2(clp: vs.VideoNode, strength3=None, strength4=None, mode=None, dering_line_mask1=None, 
                    ps1mask=None, thickmask=None, dering_line_mask2=None) -> vs.VideoNode:
    def chkexpr(expr: str) -> list:
        if clp.format.num_planes > 1:
            return [expr, ""]
        else:
            return [expr]
    
    sBitP = clp.format.bits_per_sample
    white = (1 << sBitP) - 1

    # default settings
    if mode is None:
        mode = 1
    else:
        if not isinstance(mode, int):
            raise TypeError('\"mode\" invalid! [1-3]')
    
    # preset for strength
    pnum = mode - 1
    if strength3 is None: strength3 = [100, 100, 255][pnum]
    if strength4 is None: strength4 = [0.6, 0.6,   0][pnum]
    strength3 = round(strength3 / 255 * white)
    # strength4 = round(strength4 / 255 * white)
    
    x = round((clp.width / 4) * 4)
    y = round((clp.height / 4) * 4)
    x2 = int(x / 2)
    y2 = int(y / 2)
    xs = int(x * 3 / 2)
    ys = int(y * 3 / 2)
    
    # mask
    if dering_line_mask1 is None:
        dering_line_mask1 = edge_detect(clp, "sobel", 4, 255, 0, 0)
    if ps1mask is None:
        ps1mask = dering_line_mask1.std.Levels(0, round(90 / 255 * white), 3.3, 0, white).rgvs.RemoveGrain(11)
    if thickmask is None:
        thickmask = dering_line_mask1.std.Inflate().std.Inflate().std.Inflate()
        thickmask = thickmask.std.Levels(0, round(90 / 255 * white), 3.3, 0, white).rgvs.RemoveGrain(11)
        thickmask = thickmask.std.Inflate().std.Inflate().std.Levels(0, white, 3.3, 0, white)
        thickmask = thickmask.std.Inflate().std.Inflate()
    if dering_line_mask2 is None:
        ps1mask_ivt = ps1mask.std.Invert()
        dering_line_mask2 = core.std.Expr([ps1mask_ivt, thickmask], [f"x y * {white} /"])
    
    ps1 = core.std.MaskedMerge(
        clipa = clp, 
        clipb = clp.rgvs.RemoveGrain(20), 
        mask = dering_line_mask2.std.Levels(round(60 / 255 * white), round(140 / 255 * white), 3.0, 0, strength3),
        first_plane = True
    )
    
    # dehalo
    halo = ps1.resize.Bicubic(width=x2, height=y2).resize.Bicubic(
        width = x,
        height = y, 
        filter_param_a = 1, 
        filter_param_b = 0, 
        filter_param_a_uv = 1, 
        filter_param_b_uv = 0
    )
    halo_mask1 = core.std.Expr([ps1.std.Maximum(), clp.std.Minimum()], chkexpr("x y -"))
    halotomask = core.std.Expr([halo.std.Maximum(), halo.std.Minimum()], chkexpr("x y -"))
    num1 = round(0.001 / 255 * white)
    num2 = round(50 / 255 * white)
    num3 = white + 1
    num4 = round(0.5 / 255 * white)
    num5 = round(512 / 255 * white)
    halotomask2 = core.std.Expr(
        clips = [halotomask, halo_mask1], 
        expr = [f"y x - y {num1} + / {white} * {num2} - y {num3} + {num5} / {num4} + *"]
    )
    pshalo = core.std.MaskedMerge(halo, ps1, halotomask2, [0], True)
    pshalo2 = core.resize.Lanczos(ps1, xs, ys, filter_param_a=4, resample_filter_uv="spline36")
    pshalo2 = core.std.Expr([pshalo.std.Maximum().resize.Bicubic(xs, ys), pshalo2], chkexpr("x y min"))
    pshalo2 = core.std.Expr([pshalo.std.Minimum().resize.Bicubic(xs, ys), pshalo2], chkexpr("x y max"))
    pshalo2 = core.resize.Lanczos(pshalo2, x, y, filter_param_a=4, resample_filter_uv="spline36")
    if mode != 3:
        ps2 = core.std.Expr([ps1, pshalo2], chkexpr(f"x y < x x y - {strength4} * - x x y - 1 * - ?"))
    else:
        ps2 = ps1
    return ps2
    
    
def SHDdering(clip: vs.VideoNode, mode=None, strength1=None, strength2=None, strength3=None, strength4=None, 
              twomask=None) -> vs.VideoNode:
    sBitP = clip.format.bits_per_sample
    white = (1 << sBitP) - 1

    # default settings
    if mode is None:
        mode = 1
    else:
        if not isinstance(mode, int):
            raise TypeError('\"mode\" invalid! [1-3]')
    if twomask is None:
        twomask = False
    
    # preset for strength
    pnum = mode - 1
    if strength1 is None: strength1 = [100, 125, 255][pnum]
    if strength2 is None: strength2 = [0.6, 1.0,   0][pnum]
    if strength3 is None: strength3 = [100, 100, 255][pnum]
    if strength4 is None: strength4 = [0.6, 0.6,   0][pnum]
    
    # mask
    dering_line_mask1 = edge_detect(clip, "sobel", 4, 255, 0, 0)
    ps1mask = dering_line_mask1.std.Levels(0, round(90 / 255 * white), 3.3, 0, white).rgvs.RemoveGrain(11)
    thickmask = dering_line_mask1.std.Inflate().std.Inflate().std.Inflate()
    thickmask = thickmask.std.Levels(0, round(90 / 255 * white), 3.3, 0, white).rgvs.RemoveGrain(11)
    thickmask = thickmask.std.Inflate().std.Inflate().std.Levels(0, white, 3.3, 0, white)
    thickmask = thickmask.std.Inflate().std.Inflate()
    ps1mask_ivt = ps1mask.std.Invert()
    dering_line_mask2 = core.std.Expr([ps1mask_ivt, thickmask], [f"x y * {white} /"])
    
    pro1 = dering_process(clip, strength1, strength2, mode, dering_line_mask1, ps1mask, thickmask, dering_line_mask2)
    
    # mask
    if twomask:
        dering_line_mask1 = edge_detect(pro1, "sobel", 4, 255, 0, 0)
        ps1mask = dering_line_mask1.std.Levels(0, round(90 / 255 * white), 3.3, 0, white).rgvs.RemoveGrain(11)
        thickmask = dering_line_mask1.std.Inflate().std.Inflate().std.Inflate()
        thickmask = thickmask.std.Levels(0, round(90 / 255 * white), 3.3, 0, white).rgvs.RemoveGrain(11)
        thickmask = thickmask.std.Inflate().std.Inflate().std.Levels(0, white, 3.3, 0, white)
        thickmask = thickmask.std.Inflate().std.Inflate()
        ps1mask_ivt = ps1mask.std.Invert()
        dering_line_mask2 = core.std.Expr([ps1mask_ivt, thickmask], [f"x y * {white} /"])
        
    pro2 = dering_process2(pro1, strength3, strength4, mode, dering_line_mask1, ps1mask,thickmask, dering_line_mask2)

    return mask_process(clip, pro1=pro1, prepro2=pro1, pro2=pro2)

    
def expand_limit(src: vs.VideoNode, threshold=None) -> vs.VideoNode:
    sBitP = src.format.bits_per_sample
    white = (1 << sBitP) - 1
    if threshold is None:
        threshold = 42
    threshold = round(threshold / 255 * white)
    return src.std.Maximum(threshold=threshold, coordinates=[0, 0, 0, 1, 1, 0, 0, 0], planes=0)


def inpand_limit(src: vs.VideoNode, threshold=None) -> vs.VideoNode:
    sBitP = src.format.bits_per_sample
    white = (1 << sBitP) - 1
    if threshold is None:
        threshold = 42
    threshold = round(threshold / 255 * white)
    return src.std.Minimum(threshold=threshold, coordinates=[0, 0, 0, 1, 1, 0, 0, 0], planes=0)
    
    
### Main Process ### 
####################
def Sdering_mod(clip, mode=None, twomask=None):
    def chkexpr(expr: str) -> list:
        if clip.format.num_planes > 1:
            return [expr, ""]
        else:
            return [expr]
    
    sBitP = clip.format.bits_per_sample
    white = (1 << sBitP) - 1

    # default settings
    if mode is None:
        mode = 1
    else:
        if not isinstance(mode, int):
            raise TypeError('\"mode\" invalid! [1-3]')
    if twomask is None:
        twomask = False

    x = round((clip.width / 4) * 4)
    y = round((clip.height / 4) * 4)
    xs = int(x * 3 / 2)
    ys = int(y * 3 / 2)

    # mask
    ei_mask = expand_limit(clip)
    ei_mask = inpand_limit(ei_mask)
    num1 = round(191 / 255 * white)
    num2 = round(4 / 255 * white)
    num3 = round(127 / 255 * white)
    num4 = 1
    diffexp = f"y {num1} < y {num1} ? x {num2} + > x y {num1} < y {num1} ? - 0 ? {num3} +"
    diff1 = core.std.Expr([clip, ei_mask], chkexpr(diffexp))
    if mode == 1:
        dering1 = mask_process(clip)
        dering1 = expand_limit(dering1)
        dering1 = inpand_limit(dering1)
    else:
        dering1 = core.resize.Lanczos(clip, xs, ys, filter_param_a=4, resample_filter_uv="spline36")
        dering1 = SHDdering(dering1, twomask=twomask).resize.Lanczos(
            width = x, 
            height = y, 
            filter_param_a = 4,
            resample_filter_uv = "spline36"
        )
        dering1 = expand_limit(dering1)
        dering1 = inpand_limit(dering1)
    thinexp = f"x y {num3} - 0 {num4} + * +"
    thin = core.std.Expr([dering1, diff1], chkexpr(thinexp))
    if mode == 1:
        dering2 = core.resize.Lanczos(thin, xs, ys, filter_param_a=4, resample_filter_uv="spline36")
        dering2 = SHDdering(dering2, twomask=twomask).resize.Lanczos(
            width = x, 
            height = y, 
            filter_param_a = 4,
            resample_filter_uv = "spline36"
        )
        dering2 = expand_limit(dering2)
        dering2 = inpand_limit(dering2)
    else:
        dering2 = core.resize.Lanczos(thin, xs * 2, ys * 2, filter_param_a=4, resample_filter_uv="spline36")
        dering2 = mask_process(dering2).resize.Lanczos(x, y, filter_param_a=4, resample_filter_uv="spline36")
        dering2 = expand_limit(dering2)
        dering2 = inpand_limit(dering2)

    final = core.std.Expr([dering2, diff1], chkexpr(thinexp))

    if mode == 1:
        pp = SHDdering(final, twomask=twomask)
    elif mode == 3:
        pp = thin
    else:
        pp = final
        
    return pp
