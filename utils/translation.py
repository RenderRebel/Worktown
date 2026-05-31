import urllib.parse
import requests

def translate_to_hindi(text: str) -> str:
    """Translates the given English text to Hindi using Google's free translation API."""
    if not text or not isinstance(text, str):
        return text
    try:
        url = f"http://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=hi&dt=t&q={urllib.parse.quote(text)}"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            result = response.json()
            # The result format is [[[translated_text, source_text, ...]]]
            translated = "".join([sentence[0] for sentence in result[0] if sentence[0]])
            return translated
    except Exception:
        pass
    return text


def translate_fields_recursively(data, cache=None):
    """Recursively search and translate user-facing fields inside response dicts/lists to Hindi."""
    if cache is None:
        cache = {}
        
    if isinstance(data, dict):
        new_dict = {}
        for k, v in data.items():
            if k in ["title", "description", "bio", "address", "cancel_reason", "message", "detail", "name"]:
                if isinstance(v, str):
                    if v not in cache:
                        cache[v] = translate_to_hindi(v)
                    new_dict[k] = cache[v]
                elif isinstance(v, list):
                    translated_list = []
                    for item in v:
                        if isinstance(item, str):
                            if item not in cache:
                                cache[item] = translate_to_hindi(item)
                            translated_list.append(cache[item])
                        else:
                            translated_list.append(translate_fields_recursively(item, cache))
                    new_dict[k] = translated_list
                else:
                    new_dict[k] = translate_fields_recursively(v, cache)
            elif k == "skills":
                if isinstance(v, list):
                    translated_list = []
                    for item in v:
                        if isinstance(item, str):
                            if item not in cache:
                                cache[item] = translate_to_hindi(item)
                            translated_list.append(cache[item])
                        else:
                            translated_list.append(translate_fields_recursively(item, cache))
                    new_dict[k] = translated_list
                elif isinstance(v, str):
                    if v not in cache:
                        cache[v] = translate_to_hindi(v)
                    new_dict[k] = cache[v]
                else:
                    new_dict[k] = translate_fields_recursively(v, cache)
            else:
                new_dict[k] = translate_fields_recursively(v, cache)
        return new_dict
    elif isinstance(data, list):
        return [translate_fields_recursively(item, cache) for item in data]
    return data
