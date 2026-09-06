# Referencias visuales de gestos — leer esto primero

Esta carpeta tiene **dos conjuntos de imágenes que NO son lo mismo**. Confundirlos
fue exactamente el error que originó la auditoría
[`openspec/changes/hand-sign-fidelity/AUDIT.md`](../../openspec/changes/hand-sign-fidelity/AUDIT.md).

## `canonical/` — los 14 sellos REALES (autoritativo)

Las 14 imágenes del README de
[NARUTO-HandSignDetection](https://github.com/Kazuhito00/NARUTO-HandSignDetection)
(Kazuhito Takahashi, MIT), fotografiadas por el propio autor y usadas para entrenar
su modelo. **Los 14 sellos canónicos se hacen con LAS DOS MANOS.**

`01_ne_rat` · `02_ushi_ox` · `03_tora_tiger` · `04_u_hare` · `05_tatsu_dragon` ·
`06_mi_snake` · `07_uma_horse` · `08_hitsuji_ram` · `09_saru_monkey` ·
`10_tori_bird` · `11_inu_dog` · `12_i_boar` · `13_mizunoe` · `14_gassho_clap`

Ésta es la referencia buena. Si querés saber cómo es un sello, mirá acá.

## Las imágenes sueltas de la raíz — lo que NUESTRO código detecta hoy

`naruto_tora.jpg`, `naruto_ushi.jpg`, `naruto_u.jpg`, `naruto_uma.jpg`,
`naruto_hitsuji.jpg`, `naruto_saru.png`, `naruto_inu.jpg`, `naruto_i.jpg`,
`naruto_ne.jpg`, `naruto_mi.jpg`, `naruto_tori.jpg`, `naruto_kai.jpg`,
`naruto_tatsu.jpg`, `jjk_*.jpg`, `clap.jpg`, `korean_heart.jpg`

⚠️ **Estas NO son fotos de sellos Naruto.** Son fotos de stock de gestos humanos
comunes, elegidas para que coincidan con las formas de mano que
`src/jarvis/gestures.py` busca **hoy** — que en su mayoría son invención de este
proyecto, no sellos reales (ver la auditoría). Sirven para una sola cosa: saber qué
forma hay que hacer para que el código actual dispare.

Correr el modelo real sobre estas fotos lo confirma: de las 8 formas de una mano,
sólo 2 dan detección (Tora 0.91, Hitsuji 0.47) y 6 no dan nada. Detalle completo en
la auditoría.

Excepciones — estas tres sí salieron del dataset real y son sellos legítimos (son
las mismas que están en `canonical/`): `naruto_ne.jpg`, `naruto_mi.jpg`,
`naruto_tori.jpg`.

Los índices con fuente y notas por imagen están en
[`naruto_one_hand_seals.md`](naruto_one_hand_seals.md) y
[`twohand_jjk_common_gestures.md`](twohand_jjk_common_gestures.md); ambos fueron
escritos **antes** de la auditoría y describen la fidelidad respecto de nuestro
código, no respecto del canon.

## Licencias

Varias de las imágenes sueltas son previews de bancos de imágenes
(Getty/Shutterstock/Vecteezy) con marca de agua: referencia interna, no
redistribuir. Las de `canonical/` provienen del README de un repo MIT.
