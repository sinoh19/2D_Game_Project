# Lower pit connectors

Built-in image tool; references: existing rounded lower corners and plain stone fill.

Use case: precise-object-edit. The provided image contains three32x32stone tiles enlarged: lower-left rounded corner, lower-right rounded corner, and plain stone fill. Create ONE32x32 FLAT UNDERSIDE / BOTTOM EDGE connector tile to run horizontally between these rounded lower corners. Solid muted blue-grey cave stone filling the square. TOP edge square and seamless into normal stone fill above; LEFT and RIGHT sides identical matching the rounded corners' solid outer side, so repeats have no seam. Bottom edge is a nearly straight blunt underside, at bottommost row, with restrained2-4pixel slightly darker bevel/shadow, NOT the bright top lip of a walkable floor. Keep bottom edge fully opaque across the width, do not make a floating boulder. Same exact subdued slate palette and broad low-detail stone face as reference, no new masonry, no pronounced horizontal slab lines, no isolated bright specks, no moss dots, no repeated notches. Crisp32x32pixel art with2pixel clusters, no smooth gradients or antialiasing. Single tightly framed square tile, no labels, no scenery, no outlines or cast shadow. Preserve the broad body texture, change only bottommost6logical rows.

Packaging keeps the original corner silhouettes, uses the generated underside rim on the center tile, matches horizontal seam colors, and derives collision shapes from visible stone pixels.

Final revision: use the approved upper pit corners in vertical correspondence for a small rounded lower radius; continue the existing floor rim across the underside; keep broad fill texture above it. Recompute collision from the revised silhouettes.
