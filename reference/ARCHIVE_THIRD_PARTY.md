# Dependencies and asset attribution

The implementation uses COLMAP/PyCOLMAP, OpenMVS, Open3D, OpenCV, NumPy, SciPy, Pillow, MuJoCo, OpenUSD and Playwright. These packages and binaries are not vendored; their respective upstream licenses apply. An Isaac installation is needed only for the optional Isaac scripts.

The can example derives its texture from the **YCB Object and Model Set**, attributed to Calli, Singh, Walsman, Srinivasa, Abbeel and Dollar (2015). The source record specifies **CC BY 4.0**. The photographs were cropped and projected onto an image-fitted cylinder. Preserve [the source record](demo/ycb_can/sources.json) and [CC BY 4.0 attribution terms](https://creativecommons.org/licenses/by/4.0/) when redistributing these derived assets.

The RGB-D methods support the TUM RGB-D benchmark and Redwood livingroom1. Redwood livingroom1 is a synthetic ICL-NUIM-derived sequence, not a real room capture. Relevant research attribution includes Handa et al. (2014) and Choi et al. (2015). These datasets are not bundled; obtain them from their original providers and follow their terms.

Office and pantry renders/models derive from supplied room videos. Original source videos and photographs are not bundled. The derived assets retain photographed signage and packaging; they are not anonymized or assigned a separate public-data license. Brands shown in textures remain those of their owners.

Unrelated third-party pretrained room assets and downloaded renderers are excluded. No blanket license is assigned to this repository; choose an appropriate license for project-owned code before public distribution without overriding third-party data terms.
