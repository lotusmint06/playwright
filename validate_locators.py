"""
locators.json 정합성 검증 스크립트

검증 항목:
1. JSON 형식 유효성
2. 필수 필드 존재 여부 (primary, previous, healed)
3. 동적 locator에 {value} 포함 여부
4. scripts/ 에서 참조하는 section/key가 locators.json에 존재하는지
5. fallback 형식 유효성 및 text= strict mode 위험 경고
"""

import json
import os
import re
import sys

LOCATORS_FILE = "locators.json"
SCRIPTS_DIR = "scripts"
REQUIRED_FIELDS = {"primary", "previous", "healed"}
DYNAMIC_PREFIXES = ("text=",)


def validate_json_format() -> dict:
    with open(LOCATORS_FILE, encoding="utf-8") as f:
        locators = json.load(f)
    print("✅ JSON 형식 유효")
    return locators


def validate_fields(locators: dict) -> list[str]:
    errors = []
    for section, keys in locators.items():
        for key, value in keys.items():
            missing = REQUIRED_FIELDS - set(value.keys())
            if missing:
                errors.append(f"  [{section}.{key}] 필수 필드 누락: {missing}")
    return errors


def validate_dynamic_locators(locators: dict) -> list[str]:
    warnings = []
    for section, keys in locators.items():
        for key, value in keys.items():
            primary = value.get("primary", "")
            is_dynamic = any(primary.startswith(p) for p in DYNAMIC_PREFIXES)
            if is_dynamic and "{value}" not in primary:
                warnings.append(
                    f"  ⚠️  [{section}.{key}] 동적 locator이지만 {{value}} 없음: {primary}"
                )
    return warnings


def validate_fallback_format(locators: dict) -> list[str]:
    errors = []
    warnings = []
    for section, keys in locators.items():
        for key, value in keys.items():
            fallback = value.get("fallback")
            if fallback is None:
                continue

            items = fallback if isinstance(fallback, list) else [fallback]
            for fb in items:
                if not isinstance(fb, str) or not fb.strip():
                    errors.append(f"  [{section}.{key}] 유효하지 않은 fallback: {fb}")
                elif fb.startswith("text=") and "{value}" not in fb:
                    warnings.append(
                        f"  ⚠️  [{section}.{key}] text= fallback은 strict mode 위반 가능: {fb}"
                    )
    return errors, warnings


def validate_script_references(locators: dict) -> list[str]:
    """scripts/ 파일에서 locators[section][key] 패턴을 추출해 존재 여부 확인"""
    errors = []
    if not os.path.isdir(SCRIPTS_DIR):
        return errors

    pattern = re.compile(r'self\.locators\["(\w+)"\]\["(\w+)"\]')

    for filename in os.listdir(SCRIPTS_DIR):
        if not filename.endswith(".py"):
            continue
        filepath = os.path.join(SCRIPTS_DIR, filename)
        with open(filepath, encoding="utf-8") as f:
            content = f.read()

        for match in pattern.finditer(content):
            section, key = match.group(1), match.group(2)
            if section not in locators:
                errors.append(f"  [{filename}] 섹션 없음: '{section}'")
            elif key not in locators[section]:
                errors.append(f"  [{filename}] key 없음: '{section}.{key}'")

    return errors


def main():
    print(f"🔍 {LOCATORS_FILE} 검증 시작\n")
    errors = []
    warnings = []

    try:
        locators = validate_json_format()
    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 실패: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"❌ {LOCATORS_FILE} 파일 없음")
        sys.exit(1)

    field_errors = validate_fields(locators)
    if field_errors:
        errors.extend(field_errors)
    else:
        print("✅ 필수 필드 검증 통과")

    dynamic_warnings = validate_dynamic_locators(locators)
    if dynamic_warnings:
        warnings.extend(dynamic_warnings)
    else:
        print("✅ 동적 locator 검증 통과")

    fallback_errors, fallback_warnings = validate_fallback_format(locators)
    if fallback_errors:
        errors.extend(fallback_errors)
    if fallback_warnings:
        warnings.extend(fallback_warnings)
    if not fallback_errors and not fallback_warnings:
        print("✅ fallback 형식 검증 통과")

    ref_errors = validate_script_references(locators)
    if ref_errors:
        errors.extend(ref_errors)
    else:
        print("✅ scripts/ 참조 검증 통과")

    if warnings:
        print("\n경고:")
        for w in warnings:
            print(w)

    if errors:
        print("\n오류:")
        for e in errors:
            print(e)
        print(f"\n❌ 검증 실패 ({len(errors)}건)")
        sys.exit(1)

    print("\n✅ 모든 검증 통과")


if __name__ == "__main__":
    main()
