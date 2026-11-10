"""Build a six-character, licensed heading font; no font dependency at runtime."""
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools import subset

OUT=Path(__file__).resolve().parent/'fonts'
OUT.mkdir(exist_ok=True)
font=TTFont('C:/Windows/Fonts/NotoSerifSC-VF.ttf')
license_text=(OUT/'OFL.txt').read_text('utf8').split('SIL Open Font License',1)[1]
notice='Copyright 2017-2023 Adobe. Based on Noto Serif SC; modified static subset for EVA 02.\n\n'+'SIL Open Font License'+license_text
options=subset.Options()
options.name_IDs=['*']
subsetter=subset.Subsetter(options=options)
subsetter.populate(text='EVA 02')
subsetter.subset(font)
font=instantiateVariableFont(font,{'wght':900},inplace=True)
for name_id,value in [(1,'EVA Heading'),(2,'Black'),(3,'EVAHeading-Black-subset'),(4,'EVA Heading Black'),(6,'EVAHeading-Black'),(13,notice)]:
    font['name'].removeNames(nameID=name_id)
    font['name'].setName(value,name_id,3,1,0x409)
font.save(OUT/'eva-heading.ttf')
(OUT/'OFL.txt').write_text(notice,'utf8')
print({'fontBytes':(OUT/'eva-heading.ttf').stat().st_size})
