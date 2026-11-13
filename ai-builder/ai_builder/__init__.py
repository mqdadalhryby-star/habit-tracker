"""ai-builder — نموذج ذكاء اصطناعي يحوّل طلباً نصياً إلى مشروع يعمل.

الاستخدام المختصر:
    from ai_builder import BuilderModel
    result = BuilderModel().build("أنشئ لي أداة تنظف ملفات CSV", out_dir="./out")
    print(result.project_dir)
"""

from .spec import Spec, KINDS
from .model import BuilderModel, BuildResult
from .intent import analyze

__all__ = ["Spec", "KINDS", "BuilderModel", "BuildResult", "analyze"]
__version__ = "1.0.0"
