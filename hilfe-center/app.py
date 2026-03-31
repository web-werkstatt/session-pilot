"""
CMS Hilfe-Center
Flask App fuer die Dokumentation von Contypio.

Markdown-Dateien mit YAML-Frontmatter.
Hot-Reload: Dateiaenderungen werden automatisch erkannt.
"""

import os
import glob
import re
from datetime import datetime
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import yaml
import markdown
import frontmatter

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'cms-help-secret-change-me')
CORS(app)

URL_PREFIX = os.environ.get('URL_PREFIX', '').rstrip('/')

@app.context_processor
def inject_url_prefix():
    return {'url_prefix': URL_PREFIX}

CONTENT_DIR = os.path.join(os.path.dirname(__file__), 'content')

_content_cache = {'data': None, 'timestamp': 0}


def generate_toc_from_html(html_content):
    """Extract h2/h3 headings and add IDs for TOC linking."""
    toc = []
    heading_pattern = re.compile(r'<(h[23])>(.*?)</\1>', re.IGNORECASE)

    def add_id(match):
        tag = match.group(1)
        text = match.group(2)
        clean = re.sub(r'<[^>]+>', '', text)
        slug = re.sub(r'[^a-z0-9]+', '-', clean.lower()).strip('-')
        level = int(tag[1])
        toc.append({'id': slug, 'title': clean, 'level': level})
        return f'<{tag} id="{slug}">{text}</{tag}>'

    html_content = heading_pattern.sub(add_id, html_content)
    return html_content, toc


def get_content_mtime():
    """Get newest modification time across all content files."""
    mtime = 0
    config_file = os.path.join(CONTENT_DIR, '_config.yaml')
    if os.path.exists(config_file):
        mtime = max(mtime, os.path.getmtime(config_file))
    for md_file in glob.glob(os.path.join(CONTENT_DIR, '**/*.md'), recursive=True):
        mtime = max(mtime, os.path.getmtime(md_file))
    return mtime


def load_help_content():
    """Load help content from Markdown files with hot-reload."""
    global _content_cache

    current_mtime = get_content_mtime()
    if _content_cache['data'] and _content_cache['timestamp'] >= current_mtime:
        return _content_cache['data']

    config_file = os.path.join(CONTENT_DIR, '_config.yaml')
    config = {}
    if os.path.exists(config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}

    topics = {}
    md_extensions = ['tables', 'fenced_code', 'codehilite', 'toc', 'attr_list']

    for md_file in glob.glob(os.path.join(CONTENT_DIR, '**/*.md'), recursive=True):
        try:
            post = frontmatter.load(md_file)
            rel_path = os.path.relpath(md_file, CONTENT_DIR)
            path_id = os.path.splitext(rel_path)[0].replace(os.sep, '/')
            topic_id = post.get('id', path_id)
            parent_id = os.path.dirname(path_id) if '/' in path_id else None

            html_content = markdown.markdown(
                post.content, extensions=md_extensions, output_format='html5'
            )
            manual_toc = post.get('toc', [])
            if manual_toc:
                toc = manual_toc
            else:
                html_content, toc = generate_toc_from_html(html_content)

            topics[topic_id] = {
                'id': topic_id, 'path_id': path_id, 'parent': parent_id,
                'children': [],
                'title': post.get('title', topic_id.split('/')[-1].replace('-', ' ').title()),
                'icon': post.get('icon', 'file-text'),
                'description': post.get('description', ''),
                'section': post.get('section', 'Allgemein'),
                'tags': post.get('tags', []),
                'related': post.get('related', []),
                'tips': post.get('tips', []),
                'badge': post.get('badge', ''),
                'toc': toc, 'content': html_content,
                'order': post.get('order', 999),
            }
        except Exception as e:
            app.logger.error(f"Error loading {md_file}: {e}")

    for topic in topics.values():
        pid = topic.get('parent')
        if pid and pid in topics:
            topics[pid]['children'].append(topic['id'])

    sections = config.get('sections', [])
    if sections:
        for section in sections:
            section_topics = []
            for tid in section.get('topics', []):
                if tid in topics:
                    section_topics.append(topics[tid])
            section['topics'] = sorted(section_topics, key=lambda x: x.get('order', 999))
    else:
        section_map = {}
        for topic in topics.values():
            sn = topic.get('section', 'Allgemein')
            if sn not in section_map:
                section_map[sn] = {'title': sn, 'icon': 'folder', 'topics': []}
            section_map[sn]['topics'].append(topic)
        sections = list(section_map.values())
        for s in sections:
            s['topics'] = sorted(s['topics'], key=lambda x: x.get('order', 999))

    result = {
        'sections': sections,
        'all_topics': topics,
        'last_updated': datetime.now().isoformat(),
    }
    _content_cache['data'] = result
    _content_cache['timestamp'] = current_mtime
    return result


def find_topic(topic_id):
    content = load_help_content()
    return content.get('all_topics', {}).get(topic_id)


@app.route('/health')
def health():
    return jsonify({'status': 'healthy', 'service': 'cms-help'}), 200


@app.route('/')
def index():
    content = load_help_content()
    return render_template('index.html', content=content)


@app.route('/topic/<path:topic_id>')
def topic(topic_id):
    content = load_help_content()
    topic_data = find_topic(topic_id)
    if not topic_data:
        return render_template('404.html', content=content, topic_id=topic_id), 404

    parent_topic = None
    if topic_data.get('parent'):
        parent_topic = find_topic(topic_data['parent'])

    child_topics = sorted(
        [find_topic(cid) for cid in topic_data.get('children', []) if find_topic(cid)],
        key=lambda x: x.get('order', 999),
    )

    return render_template(
        'topic.html', topic=topic_data, parent_topic=parent_topic,
        child_topics=child_topics, content=content,
    )


@app.route('/search')
def search():
    query = request.args.get('q', '').lower().strip()
    content = load_help_content()
    results = []

    if query and len(query) >= 2:
        for topic in content.get('all_topics', {}).values():
            score = 0
            if query in topic.get('title', '').lower():
                score += 100
            for tag in topic.get('tags', []):
                if query in str(tag).lower():
                    score += 50
            if query in topic.get('description', '').lower():
                score += 30
            if query in topic.get('content', '').lower():
                score += 10
            if score > 0:
                results.append({
                    'id': topic['id'], 'title': topic['title'],
                    'description': topic.get('description', ''),
                    'section': topic.get('section'), 'score': score,
                })
        results = sorted(results, key=lambda x: x['score'], reverse=True)

    return render_template('search.html', query=query, results=results, content=content)


@app.route('/api/search')
def api_search():
    query = request.args.get('q', '').lower().strip()
    content = load_help_content()
    results = []
    if query and len(query) >= 2:
        for topic in content.get('all_topics', {}).values():
            score = 0
            if query in topic.get('title', '').lower():
                score += 100
            for tag in topic.get('tags', []):
                if query in str(tag).lower():
                    score += 50
            if query in topic.get('description', '').lower():
                score += 30
            if query in topic.get('content', '').lower():
                score += 10
            if score > 0:
                results.append({
                    'id': topic['id'], 'title': topic['title'],
                    'description': topic.get('description', ''),
                    'section': topic.get('section'), 'score': score,
                })
        results = sorted(results, key=lambda x: x['score'], reverse=True)
    return jsonify({'results': results})


@app.route('/sitemap.xml')
def sitemap():
    content = load_help_content()
    base_url = 'https://doc.session-pilot.com'
    today = datetime.now().strftime('%Y-%m-%d')

    urls = [f'''  <url>
    <loc>{base_url}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>''']

    for topic in content.get('all_topics', {}).values():
        priority = '0.8' if topic.get('order', 999) <= 3 else '0.6'
        urls.append(f'''  <url>
    <loc>{base_url}/topic/{topic["id"]}</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>{priority}</priority>
  </url>''')

    xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>'''

    return app.response_class(xml, mimetype='application/xml')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
