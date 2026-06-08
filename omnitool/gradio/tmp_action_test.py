import asyncio
import json
import traceback
from tools.computer import ComputerTool


async def main():
    tool = ComputerTool(is_scaling=False)

    # Start from a relatively safe desktop corner.
    await tool(action='mouse_move', coordinate=(50, 50))

    tests = [
        ('cursor_position', {'action': 'cursor_position'}),
        ('mouse_move', {'action': 'mouse_move', 'coordinate': (120, 120)}),
        ('left_click', {'action': 'left_click'}),
        ('double_click', {'action': 'double_click'}),
        ('right_click', {'action': 'right_click'}),
        ('key_escape', {'action': 'key', 'text': 'Escape'}),
        ('middle_click', {'action': 'middle_click'}),
        ('left_click_drag', {'action': 'left_click_drag', 'coordinate': (180, 180)}),
        ('scroll_up', {'action': 'scroll_up'}),
        ('scroll_down', {'action': 'scroll_down'}),
        ('hover', {'action': 'hover'}),
        ('wait', {'action': 'wait'}),
        ('type', {'action': 'type', 'text': 'omnitool_action_test'}),
        ('screenshot', {'action': 'screenshot'}),
    ]

    results = []
    for name, kwargs in tests:
        try:
            res = await tool(**kwargs)
            results.append({
                'action': name,
                'ok': True,
                'output': getattr(res, 'output', None),
                'has_image': bool(getattr(res, 'base64_image', None)),
            })
        except Exception as e:
            results.append({
                'action': name,
                'ok': False,
                'error': str(e),
                'trace': traceback.format_exc(limit=1).strip(),
            })

    print(json.dumps(results, indent=2))


asyncio.run(main())
