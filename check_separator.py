import inspect
import sys
sys.path.insert(0, r'F:\dev\Python\voice-revolver-local-ai\venv-mdx\Lib\site-packages')

from audio_separator.separator import Separator

print("Separator.load_model parameters:")
print("=" * 50)
sig = inspect.signature(Separator.load_model)
for name, param in sig.parameters.items():
    if name == 'self':
        continue
    default = param.default if param.default != inspect.Parameter.empty else "REQUIRED"
    print(f"{name}: {default}")
