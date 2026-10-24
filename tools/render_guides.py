"""Render the repository's limited Markdown guide format as offline Pages HTML.
The Markdown files are the source of truth. No network or Markdown dependency.
"""
from html import escape
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
GUIDES={'OWN_VIDEO.md':('guide.html','Use your own video'),'FUTURE_WORK.md':('future.html','Future work')}


def inline(text):
    tokens=[]
    def protect(value):tokens.append(value);return f'\x00{len(tokens)-1}\x00'
    text=re.sub(r'`([^`]+)`',lambda m:protect('<code>'+escape(m[1])+'</code>'),text)
    def link(m):
        target=m[2]
        if target in GUIDES:target=GUIDES[target][0]
        if not (target.startswith(('https://','http://','#')) or target in ('guide.html','future.html')):
            raise ValueError(f'Unmapped guide link: {target}')
        return protect('<a href="'+escape(target,quote=True)+'">'+escape(m[1])+'</a>')
    text=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',link,text)
    text=escape(text)
    text=re.sub(r'\*\*(.+?)\*\*',r'<strong>\1</strong>',text)
    return re.sub(r'\x00(\d+)\x00',lambda m:tokens[int(m[1])],text)


def render(markdown):
    lines=markdown.splitlines();out=[];toc=[];i=0
    while i<len(lines):
        line=lines[i]
        if not line.strip():i+=1;continue
        if line.startswith('```'):
            language=line[3:].strip();body=[];i+=1
            while i<len(lines) and not lines[i].startswith('```'):body.append(lines[i]);i+=1
            if i==len(lines):raise ValueError('Unclosed guide code block')
            out.append('<div class="code-block"><button type="button" class="copy-code">Copy</button><pre><code class="language-'+escape(language)+'">'+escape('\n'.join(body))+'</code></pre></div>');i+=1;continue
        match=re.match(r'^(#{1,4}) (.+)$',line)
        if match:
            level=len(match[1]);title=match[2];identifier=re.sub(r'[^a-z0-9]+','-',title.lower()).strip('-')
            out.append(f'<h{level} id="{identifier}">'+inline(title)+f'</h{level}>')
            if level==2:toc.append((identifier,title))
            i+=1;continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].startswith('|'):
                cells=[x.strip() for x in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?',c) for c in cells):rows.append(cells)
                i+=1
            out.append('<div class="table-scroll"><table><thead><tr>'+''.join('<th>'+inline(c)+'</th>' for c in rows[0])+'</tr></thead><tbody>')
            out.extend('<tr>'+''.join('<td>'+inline(c)+'</td>' for c in row)+'</tr>' for row in rows[1:]);out.append('</tbody></table></div>');continue
        list_match=re.match(r'^(- |\d+\. )(.+)$',line)
        if list_match:
            ordered=list_match[1]!='- ';tag='ol' if ordered else 'ul';out.append('<'+tag+'>')
            while i<len(lines):
                item=re.match(r'^(\d+\. |\- )(.+)$',lines[i])
                if not item or (item[1]!='- ')!=ordered:break
                out.append('<li>'+inline(item[2])+'</li>');i+=1
            out.append('</'+tag+'>');continue
        paragraph=[line];i+=1
        while i<len(lines) and lines[i].strip() and not re.match(r'^(#|```|\||- |\d+\. )',lines[i]):paragraph.append(lines[i]);i+=1
        out.append('<p>'+inline(' '.join(paragraph))+'</p>')
    return '\n'.join(out),toc


def build_guides(destination):
    destination=Path(destination);outputs=[]
    for name,(filename,label) in GUIDES.items():
        body,toc=render((ROOT/'docs'/name).read_text())
        navigation=''.join('<a href="#'+identifier+'">'+escape(title)+'</a>' for identifier,title in toc)
        page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Real2Sim · '''+escape(label)+'''</title><link rel="stylesheet" href="style.css"><link rel="stylesheet" href="manual.css"><script type="module" src="project-links.js"></script><script type="module" src="manual.js"></script></head><body><header><a class="brand" href="index.html">real<span>2</span>sim</a><span class="edition">PROJECT GUIDE</span><a class="nav-link" href="guide.html">Your own video</a><a class="nav-link" href="future.html">Future work</a><a class="repo" href="guide.html" data-project-link="repository">Repository ↗</a></header><main class="manual-layout"><nav class="manual-toc" aria-label="On this page"><span class="eyebrow">ON THIS PAGE</span>'''+navigation+'''</nav><article class="manual">'''+body+'''</article></main><footer><span>Authors: <strong>Shaurya Gupta · Shreya Sajal</strong><br>Hackathon project team: <strong>random.py</strong> — Second place</span><a href="index.html">Scene gallery ↗</a></footer></body></html>'''
        path=destination/filename;path.write_text(page);outputs.append(path)
    return outputs


if __name__=='__main__':
    for path in build_guides(ROOT/'docs/mesh'):print(path)
