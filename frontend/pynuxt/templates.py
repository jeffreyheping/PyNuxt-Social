"""
Jinja2 模板环境 — 全局共享实例

v0.5.1 改进：
- auto_reload=True：开发时改模板不用重启（配合 uvicorn --reload）
- DEBUG 模式：模板变量未定义时报详细错误而非静默忽略

v0.3.0 改进：
- 支持注入全局模板变量（site_name 等），所有模板自动可用
- 不再依赖 config 中的 TEMPLATE_DIRS，改为延迟初始化

使用方式：
    from pynuxt.templates import env, configure_env
    configure_env(
        template_dirs=[".", "static/js"],
        globals={"site_name": "MyApp"},
        debug=True,  # 开发模式：模板错误显示行号
    )
"""

import jinja2


def _default_globals() -> dict:
    """默认全局模板变量"""
    return {
        "site_name": "PyNuxt",
    }


class _LazyEnv:
    """延迟初始化的 Jinja2 Environment

    首次 get_template 时才创建真正的 Environment，
    允许在 import 之后、使用之前调用 configure_env()。
    """

    def __init__(self):
        self._env: jinja2.Environment | None = None
        self._template_dirs: list = ["."]
        self._globals: dict = _default_globals()
        self._debug: bool = False

    def configure(self, template_dirs: list = None, globals: dict = None,
                 debug: bool = False):
        """配置模板环境（必须在首次使用前调用）"""
        if template_dirs is not None:
            self._template_dirs = template_dirs
        if globals is not None:
            self._globals.update(globals)
        self._debug = debug
        # 重置已有的 env，下次使用时重建
        self._env = None

    def _ensure_env(self) -> jinja2.Environment:
        """确保 Environment 已创建"""
        if self._env is None:
            self._env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(self._template_dirs),
                autoescape=jinja2.select_autoescape(["html", "xml"]),
                auto_reload=True,  # 开发时改模板不用重启
                # DEBUG 模式：未定义变量报错带模板文件名+行号
                undefined=jinja2.DebugUndefined if self._debug else jinja2.Undefined,
            )
            # 注入全局变量
            for key, value in self._globals.items():
                self._env.globals[key] = value
        return self._env

    def get_template(self, name: str) -> jinja2.Template:
        """获取模板（利用 Jinja2 编译缓存 + 源文件变更检测）"""
        return self._ensure_env().get_template(name)

    def from_string(self, source: str) -> jinja2.Template:
        """从字符串创建模板"""
        return self._ensure_env().from_string(source)

    @property
    def globals(self) -> dict:
        """访问全局变量"""
        return self._ensure_env().globals


# 全局单例
env = _LazyEnv()


def configure_env(template_dirs: list = None, globals: dict = None,
                  debug: bool = False):
    """配置全局模板环境（便捷函数）

    应在 main.py 中、install_file_routing 之前调用：
        from pynuxt.templates import configure_env
        configure_env(
            template_dirs=[".", "static/js"],
            globals={"site_name": "MyApp"},
            debug=True,  # 开发模式
        )
    """
    env.configure(template_dirs=template_dirs, globals=globals, debug=debug)
