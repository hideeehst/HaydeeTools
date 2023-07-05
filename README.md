Fork of the Haydee Tools where I try to include some more features.
Original works by johnzero7, Pooka, Kein

currently it features:
- running on blender 3.3 LTS
- improved dmesh export speed (A)
- potential fix for crashing when browsing dmesh in the edith (B)
- multi mesh/dmesh Import (C)


(A) It has been observed that skeletal-meshes with 200k polygons and 50 Joints was taking around 57 minutes to export. Now the time to export has been reduced to 6 seconds.
For the lols: Export of Blender monkey with 2million polygons takes now 2 minutes, instead of 

(B) The problem may be the name of the exported object-groups inside the dmesh, when they include dots,spaces,dashes and other special characters
    
(C) Import of multiple meshes at once is now possible

Haydee Tools
=========
Blender an addon to Export/Import Haydee 1 & 2 assets.

With Blender 2.80 released there where many changes.

From v1.2.0 of this addon will only work with Blender 2.80+ (and viceversa).
For Blender 2.79 download v1.0.6

- Blender 2.80 ==> v1.2.0
- Blender 2.79 ==> v1.0.6

Main Features:

more info at:
http://johnzero7.github.io/HaydeeTools/


Difuse and Emissive textures are of the common kind.<br />
Normal maps are: RRRG (B is calculated. Normals can be converted from Edith. Tool=>Import texture. Format NormalMap)<br />
Specular maps are: R=Roughness, G=Specular intensity, B=Metallic (not properly implemented in Haydee. Leave 0)<br />
