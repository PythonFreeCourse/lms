from pathlib import Path

for module in Path(__file__).parent.glob('[!_]*.py'):
    __import__(f'{__name__}.{module.stem}', locals(), globals())


del Path
try:
    del module
except NameError:
    pass  # No modules found in the directory
