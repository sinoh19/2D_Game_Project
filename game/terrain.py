"""Continuous height queries for side-view ramp collision."""


def slope_height(slope, x, half_width=0.0):
    """Highest surface under the actor's horizontal foot span, or None."""
    left,right=slope['x1'],slope['x2']
    if x+half_width<left or x-half_width>right:return None
    a=max(left,min(right,x-half_width));b=max(left,min(right,x+half_width))
    grade=(slope['y2']-slope['y1'])/(right-left)
    return min(slope['y1']+(a-left)*grade,slope['y1']+(b-left)*grade)


def slope_surfaces(scene,x,half_width):
    return [height for slope in getattr(scene,'slopes',[])
            if (height:=slope_height(slope,x,half_width)) is not None]


def inside_slope(scene,x,feet,height,half_width):
    return any((surface:=slope_height(s,x,half_width)) is not None
               and feet>surface+.01 and feet-height<s.get('bottom',scene.layout['height'])-.01
               for s in getattr(scene,'slopes',[]))
