from pathlib import Path

path = Path('money_manager/VERSION')
current = path.read_text().strip() if path.exists() else '0.0.0'
parts = current.split('.')
while len(parts) < 3:
    parts.append('0')
major, minor, patch = (int(part) for part in parts[:3])
path.write_text(f'{major}.{minor}.{patch + 1}\n')
print(f'Bumped version: {current} -> {major}.{minor}.{patch + 1}')
