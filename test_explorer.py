import re
import requests

url = "https://explorer.xeqmlabs.com/"

response = requests.get(
    url,
    headers={"User-Agent": "EXIOM-AI/1.0"},
    timeout=8
)

response.raise_for_status()

html = response.text

# Remove scripts and styles
text = re.sub(
    r"<script.*?</script>",
    " ",
    html,
    flags=re.I | re.S
)

text = re.sub(
    r"<style.*?</style>",
    " ",
    text,
    flags=re.I | re.S
)

# Convert HTML into readable text
text = re.sub(r"<[^>]+>", "\n", text)
text = text.replace("&nbsp;", " ")
text = text.replace("&amp;", "&")

lines = [
    re.sub(r"\s+", " ", line).strip()
    for line in text.splitlines()
]

lines = [line for line in lines if line]

print("STATUS:", response.status_code)
print("HTML LENGTH:", len(html))
print("READABLE LINES:", len(lines))
print()
print("=" * 70)
print("EXPLORER READABLE CONTENT")
print("=" * 70)

for line in lines:
    print(line)