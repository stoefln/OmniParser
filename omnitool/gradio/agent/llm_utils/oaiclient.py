import os
from openai import OpenAI
from .utils import is_image_path, encode_image

def run_oai_interleaved(messages: list, system: str, model_name: str, api_key: str, max_tokens=256, temperature=0, provider_base_url: str = "https://api.openai.com/v1"):
    client = OpenAI(base_url=provider_base_url, api_key=api_key)
    deployment_model = os.getenv("OPENAI_MODEL", model_name)
    final_messages = [{"role": "system", "content": system}]

    if type(messages) == list:
        for item in messages:
            contents = []
            if isinstance(item, dict):
                for cnt in item["content"]:
                    if isinstance(cnt, str):
                        if is_image_path(cnt) and 'o3-mini' not in model_name:
                            # 03 mini does not support images
                            base64_image = encode_image(cnt)
                            content = {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                        else:
                            content = {"type": "text", "text": cnt}
                    else:
                        # in this case it is a text block from anthropic
                        content = {"type": "text", "text": str(cnt)}
                        
                    contents.append(content)
                    
                message = {"role": 'user', "content": contents}
            else:  # str
                contents.append({"type": "text", "text": item})
                message = {"role": "user", "content": contents}
            
            final_messages.append(message)

    
    elif isinstance(messages, str):
        final_messages = [{"role": "user", "content": messages}]

    try:
        request_args = {
            "model": deployment_model,
            "messages": final_messages,
        }

        if 'o1' in model_name or 'o3-mini' in model_name:
            request_args['reasoning_effort'] = 'low'
            request_args['max_completion_tokens'] = max_tokens
        else:
            request_args['max_tokens'] = max_tokens
            request_args['temperature'] = temperature

        completion = client.chat.completions.create(**request_args)
        text = completion.choices[0].message.content
        token_usage = int(getattr(completion.usage, "total_tokens", 0) or 0)
        if text is None:
            raise RuntimeError("LLM response had empty content")
        return text, token_usage
    except Exception as e:
        raise RuntimeError(f"Error in OpenAI/Azure request: {e}") from e