'''
python -m omniparserserver --som_model_path ../../weights/icon_detect/model.pt --caption_model_name florence2 --caption_model_path ../../weights/icon_caption_florence --device cuda --BOX_TRESHOLD 0.05
'''

import os
import sys

import uvicorn

root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.append(root_dir)

try:
    from .service import OmniParserRuntime, OmniParserSettings, build_arg_parser, create_app
except ImportError:
    from service import OmniParserRuntime, OmniParserSettings, build_arg_parser, create_app


runtime = OmniParserRuntime(OmniParserSettings.from_env())
app = create_app(runtime)


def main() -> None:
    args = build_arg_parser().parse_args()
    settings = OmniParserSettings.from_args(args)
    uvicorn.run(create_app(OmniParserRuntime(settings)), host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()