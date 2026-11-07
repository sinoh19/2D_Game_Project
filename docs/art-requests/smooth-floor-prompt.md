# Smooth floor top edit

Built-in image tool; edit target: existing cave floor; reference: matching stair.

Use case: precise-object-edit. Image1 is the EDIT TARGET: existing32x32 stone floor tile. Image2 is matching stair tile STYLE reference. Change ONLY the uppermost6logical pixel rows of the floor tile: flatten the walkable upper contour and make its thin light stone rim flow smoothly into the stair's light edge. Remove the obvious repeated deep dark notches and scalloped bumps. Keep a nearly horizontal continuous top surface, fully opaque from top row, with only subtle1-2px internal chips and gently varied2pixel rim thickness. Keep LEFT and RIGHT edge heights identical, so repeats join without a visible seam. Preserve the exact blue-grey palette, body texture and shading below top6rows; do not repaint entire rock face. Native32x32 pixel art, visible large crisp square pixel clusters, no antialiasing or gradients. NOT brick, not a polished slab, still rough natural cave stone. Output one tightly framed single square tile; no margins, no labels, no new objects, no border, no glow. Transparent background permitted only outside tile, but main square is opaque.

Packaging: retain every original pixel below row6, use only original stone RGB colors for the edited rim, update only the Floor cell's top6rows in the Tiled atlas.
