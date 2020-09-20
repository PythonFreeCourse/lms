from pathlib import Path

for module in Path(__file__).parent.glob('[!_]*.py'):
    __import__(f'{__name__}.{module.stem}', locals(), globals())
    del module  # we don't want to expose the module due to this import

del Path
