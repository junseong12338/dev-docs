#!/usr/bin/env python3
"""Convert ASCII box drawings in markdown files to MkDocs Material admonitions."""
import re
import sys

def extract_title_from_box(lines):
    """Extract title from box header line."""
    for i, line in enumerate(lines[:3]):
        stripped = line.strip()
        # Check for title line (between top border and separator)
        stripped_clean = stripped.strip('│').strip()
        if stripped_clean and not stripped.startswith('┌') and not stripped.startswith('├') and not stripped.startswith('└') and not all(c in '─┼│┤├┬┴' for c in stripped_clean):
            return stripped_clean, i
    return None, -1

def determine_admonition_type(title, content):
    """Determine the best admonition type based on content."""
    combined = (title or '') + ' ' + content
    combined_lower = combined.lower()

    if any(w in combined for w in ['함정', '위험', '절대', '주의사항', '무시', '❌', '착각', '틀린', '경고']):
        return 'danger'
    if any(w in combined for w in ['핵심', '중요', '필수', '반드시', '!!', '운영 서버']):
        return 'danger'
    if any(w in combined for w in ['왜', '원리', '동작', '과정', '흐름', '시각화', '관계']):
        return 'note'
    if any(w in combined for w in ['팁', '권장', '실무', '추천']):
        return 'tip'
    if any(w in combined for w in ['비유', '예시', '시나리오']):
        return 'example'
    if any(w in combined for w in ['요약', '정리', '구조', '조감']):
        return 'abstract'
    if any(w in combined for w in ['해석', '설명', '옵션:', '분류:']):
        return 'note'
    return 'note'

def process_box_content(content_lines):
    """Clean up box content lines."""
    result = []
    for line in content_lines:
        # Remove box drawing characters
        stripped = line.strip()
        if stripped.startswith('│'):
            stripped = stripped[1:]
        if stripped.endswith('│'):
            stripped = stripped[:-1]
        # Remove leading/trailing spaces but preserve relative indentation
        stripped = stripped.rstrip()
        if stripped:
            # Remove up to 2 leading spaces
            if stripped.startswith('  '):
                stripped = stripped[2:]
            elif stripped.startswith(' '):
                stripped = stripped[1:]
        result.append(stripped)
    return result

def has_inner_boxes(content_lines):
    """Check if content has inner box drawings that make it too complex."""
    inner_box_chars = 0
    for line in content_lines:
        stripped = line.strip().strip('│').strip()
        if '┌' in stripped or '└' in stripped or '├' in stripped:
            inner_box_chars += 1
    return inner_box_chars > 2

def convert_box_to_admonition(box_text, title=None):
    """Convert an ASCII box to an admonition."""
    lines = box_text.split('\n')

    # Find content lines (between borders)
    content_lines = []
    found_title = None
    title_line_idx = -1
    in_content = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith('┌'):
            in_content = True
            continue
        if stripped.startswith('└'):
            break
        if stripped.startswith('├'):
            # Separator - content before this was the title
            if content_lines and not found_title:
                # The accumulated content so far is the title area
                for cl in content_lines:
                    clean = cl.strip()
                    if clean:
                        found_title = clean
                        break
                content_lines = []
            continue
        if in_content:
            content_lines.append(line)

    if not found_title and title:
        found_title = title

    # Process content
    processed = process_box_content(content_lines)

    # Remove empty lines at start and end
    while processed and not processed[0].strip():
        processed.pop(0)
    while processed and not processed[-1].strip():
        processed.pop()

    # Determine admonition type
    adm_type = determine_admonition_type(found_title, '\n'.join(processed))

    # Build admonition
    if found_title:
        result = f'!!! {adm_type} "{found_title}"\n'
    else:
        result = f'!!! {adm_type}\n'

    result += '\n'
    for line in processed:
        if line.strip():
            result += f'    {line}\n'
        else:
            result += '\n'

    return result

def find_and_replace_boxes(text):
    """Find all ASCII box patterns wrapped in code blocks and convert them."""
    # Pattern: ``` followed by box drawing, then ```
    # We need to find code blocks that contain box drawings

    lines = text.split('\n')
    result = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Check if this is the start of a code block containing a box
        if stripped == '```':
            # Look ahead to see if next non-empty line starts a box
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1

            if j < len(lines) and lines[j].strip().startswith('┌'):
                # This is a code block with a box drawing
                # Collect everything until closing ```
                box_lines = []
                k = i + 1
                while k < len(lines) and lines[k].strip() != '```':
                    box_lines.append(lines[k])
                    k += 1

                if k < len(lines):
                    # Found closing ```
                    box_text = '\n'.join(box_lines)

                    # Check if this box has complex inner structures
                    # that should stay as code blocks
                    inner_complexity = sum(1 for bl in box_lines
                                          if '┌' in bl.strip().strip('│').strip()
                                          or '└' in bl.strip().strip('│').strip())

                    if inner_complexity > 4:
                        # Too complex, keep as code block but wrap in admonition
                        # Find title
                        title_line = None
                        for bl in box_lines[:5]:
                            clean = bl.strip().strip('│├┤').strip()
                            if clean and not clean.startswith('┌') and not clean.startswith('─') and not all(c in '─┼│' for c in clean):
                                title_line = clean
                                break

                        adm_type = determine_admonition_type(title_line, box_text)
                        if title_line:
                            result.append(f'!!! {adm_type} "{title_line}"')
                        else:
                            result.append(f'!!! {adm_type}')
                        result.append('')
                        result.append('    ```')
                        for bl in box_lines:
                            result.append(f'    {bl}')
                        result.append('    ```')
                    else:
                        # Convert to admonition
                        admonition = convert_box_to_admonition(box_text)
                        result.append(admonition.rstrip())

                    i = k + 1
                    continue

            # Not a box - check if it's just a standalone box outside code blocks
            result.append(line)
            i += 1
        elif stripped.startswith('┌'):
            # Standalone box (not in code block)
            box_lines = [line]
            k = i + 1
            while k < len(lines) and not lines[k].strip().startswith('└'):
                box_lines.append(lines[k])
                k += 1
            if k < len(lines):
                box_lines.append(lines[k])
                box_text = '\n'.join(box_lines)
                admonition = convert_box_to_admonition(box_text)
                result.append(admonition.rstrip())
                i = k + 1
                continue
            else:
                result.append(line)
                i += 1
        else:
            result.append(line)
            i += 1

    return '\n'.join(result)


def main():
    filepath = sys.argv[1]
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    converted = find_and_replace_boxes(content)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(converted)

    print(f"Converted: {filepath}")


if __name__ == '__main__':
    main()
