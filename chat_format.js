/* THIGAS AI: Markdown legível para respostas da IA.
 * Conversão para DOM usando apenas textContent e elementos criados localmente.
 * Não executa HTML do modelo, não usa innerHTML, eval nem dependências externas.
 */
(function(root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.THIGASChatFormat = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function() {
  'use strict';
  const MAX_TEXT = 64000;

  function source(value) {
    return (typeof value === 'string' ? value : String(value ?? ''))
      .slice(0, MAX_TEXT).replace(/\r\n?/g, '\n');
  }

  function heading(line) {
    const match = /^ {0,3}(#{1,6})[ \t]*(.*?)\s*$/.exec(line);
    if (!match) return null;
    // Evita transformar um fragmento de código como #include em título.
    if (match[1].length === 1 && !/^#\s/.test(line.trimStart())) return null;
    return { type: 'heading', level: match[1].length,
      text: match[2].replace(/\s+#+\s*$/, '').trim() };
  }

  function listItem(line) {
    const bullet = /^ {0,3}[-*+][ \t]+(.+)$/.exec(line);
    if (bullet) return { type: 'ul', text: bullet[1] };
    const number = /^ {0,3}(\d{1,3})[.)][ \t]+(.+)$/.exec(line);
    if (number) return { type: 'ol', start: Number(number[1]), text: number[2] };
    return null;
  }

  function rule(line) {
    return /^ {0,3}(?:\*{3,}|-{3,}|_{3,})[ \t]*$/.test(line);
  }

  function fence(line) {
    return /^ {0,3}(`{3,}|~{3,})[ \t]*([\w.+#-]*)[ \t]*$/.exec(line);
  }

  function parseBlocks(value) {
    const lines = source(value).split('\n');
    const blocks = [];
    let paragraph = [];
    function flush() {
      if (paragraph.length) {
        blocks.push({ type: 'paragraph', text: paragraph.join('\n') });
        paragraph = [];
      }
    }
    let i = 0;
    while (i < lines.length) {
      const line = lines[i];
      const trimmed = line.trim();
      if (!trimmed) {
        flush();
        i++;
        continue;
      }
      const opener = fence(line);
      if (opener) {
        flush();
        const marker = opener[1][0];
        const minLen = opener[1].length;
        const codeLines = [];
        i++;
        while (i < lines.length) {
          const end = lines[i].trim();
          if (end.length >= minLen && end.split('').every(c => c === marker)) {
            i++;
            break;
          }
          codeLines.push(lines[i++]);
        }
        blocks.push({ type: 'code', language: opener[2].slice(0, 25),
          text: codeLines.join('\n') });
        continue;
      }
      if (rule(line)) {
        flush();
        blocks.push({ type: 'rule' });
        i++;
        continue;
      }
      const title = heading(line);
      if (title) {
        flush();
        if (title.text) blocks.push(title);
        i++;
        continue;
      }
      const item = listItem(line);
      if (item) {
        flush();
        const previous = blocks[blocks.length - 1];
        if (previous && previous.type === item.type && previous.listOpen === true) {
          previous.items.push(item.text);
        } else {
          if (previous) delete previous.listOpen;
          blocks.push({ type: item.type, start: item.start || 1,
            items: [item.text], listOpen: true });
        }
        i++;
        continue;
      }
      if (blocks.length) delete blocks[blocks.length - 1].listOpen;
      if (/^ {0,3}>\s?/.test(line)) {
        flush();
        const quote = [];
        while (i < lines.length && /^ {0,3}>\s?/.test(lines[i])) {
          quote.push(lines[i++].replace(/^ {0,3}>\s?/, ''));
        }
        blocks.push({ type: 'quote', text: quote.join('\n') });
        continue;
      }
      paragraph.push(line.trim());
      i++;
    }
    flush();
    blocks.forEach(block => delete block.listOpen);
    return blocks;
  }

  function parseInline(value, level = 0) {
    const text = source(value);
    const result = [];
    let pending = '';
    const flush = () => {
      if (pending) {
        result.push({ type: 'text', text: pending });
        pending = '';
      }
    };
    let i = 0;
    while (i < text.length) {
      const char = text[i];
      if (char === '\\' && i + 1 < text.length && /[*_#`\\[\]()]/.test(text[i + 1])) {
        pending += text[i + 1];
        i += 2;
        continue;
      }
      if (char === '\n') {
        flush();
        result.push({ type: 'break' });
        i++;
        continue;
      }
      if (char === '`') {
        let count = 1;
        while (text[i + count] === '`') count++;
        const delim = '`'.repeat(count);
        const close = text.indexOf(delim, i + count);
        if (close !== -1) {
          flush();
          result.push({ type: 'code', text: text.slice(i + count, close) });
          i = close + count;
          continue;
        }
      }
      if (char === '[') {
        const link = /^\[([^\]\n]{1,160})\]\((https?:\/\/[^\s)]+)\)/i.exec(text.slice(i));
        if (link && link[2].length < 900) {
          try {
            const url = new URL(link[2]);
            if (url.protocol === 'https:' || url.protocol === 'http:') {
              flush();
              result.push({ type: 'link', text: link[1], href: url.href });
              i += link[0].length;
              continue;
            }
          } catch (_) { /* Link inválido permanece texto literal. */ }
        }
      }
      if ((char === '*' || char === '_') && level < 5) {
        if (char === '_' && /[\p{L}\d]/u.test(text[i - 1] || '') &&
          /[\p{L}\d]/u.test(text[i + 1] || '')) {
          pending += char;
          i++;
          continue;
        }
        let width = 0;
        while (width < 3 && text[i + width] === char) width++;
        const delim = char.repeat(width);
        const close = text.indexOf(delim, i + width);
        const inner = close >= 0 ? text.slice(i + width, close) : '';
        if (close >= 0 && inner.trim()) {
          flush();
          result.push({ type: width === 3 ? 'strongem' : width === 2 ? 'strong' : 'em',
            children: parseInline(inner, level + 1) });
          i = close + width;
          continue;
        }
        // Modelos por vezes enviam um marcador de abertura sem o fechamento.
        // Remove somente marcadores duplicados no começo de um trecho textual.
        if (width >= 2 && (i === 0 || /\s/.test(text[i - 1] || '')) &&
            /\S/.test(text[i + width] || '')) {
          i += width;
          continue;
        }
      }
      pending += char;
      i++;
    }
    flush();
    return result;
  }

  function appendInline(parent, tokens, doc) {
    for (const token of tokens) {
      if (token.type === 'text') {
        parent.appendChild(doc.createTextNode(token.text));
      } else if (token.type === 'break') {
        parent.appendChild(doc.createElement('br'));
      } else if (token.type === 'code') {
        const span = doc.createElement('code');
        span.textContent = token.text;
        parent.appendChild(span);
      } else if (token.type === 'link') {
        const anchor = doc.createElement('a');
        anchor.href = token.href;
        anchor.target = '_blank';
        anchor.rel = 'noopener noreferrer';
        anchor.textContent = token.text;
        parent.appendChild(anchor);
      } else {
        const tag = token.type === 'strong' ? 'strong' :
          token.type === 'em' ? 'em' : 'strong';
        const el = doc.createElement(tag);
        if (token.type === 'strongem') {
          const italic = doc.createElement('em');
          appendInline(italic, token.children, doc);
          el.appendChild(italic);
        } else {
          appendInline(el, token.children, doc);
        }
        parent.appendChild(el);
      }
    }
  }

  function render(container, value) {
    if (!container || typeof container.replaceChildren !== 'function')
      throw new TypeError('O destino precisa ser um elemento DOM.');
    const doc = container.ownerDocument || document;
    const fragment = doc.createDocumentFragment();
    for (const block of parseBlocks(value)) {
      if (block.type === 'rule') {
        fragment.appendChild(doc.createElement('hr'));
        continue;
      }
      if (block.type === 'code') {
        const pre = doc.createElement('pre');
        const code = doc.createElement('code');
        if (block.language) code.setAttribute('data-language', block.language);
        code.textContent = block.text;
        pre.appendChild(code);
        fragment.appendChild(pre);
        continue;
      }
      if (block.type === 'ul' || block.type === 'ol') {
        const list = doc.createElement(block.type);
        if (block.type === 'ol' && block.start > 1)
          list.setAttribute('start', String(block.start));
        for (const item of block.items) {
          const li = doc.createElement('li');
          appendInline(li, parseInline(item), doc);
          list.appendChild(li);
        }
        fragment.appendChild(list);
        continue;
      }
      const tag = block.type === 'heading' ? (block.level <= 2 ? 'h3' : 'h4') :
        block.type === 'quote' ? 'blockquote' : 'p';
      const element = doc.createElement(tag);
      appendInline(element, parseInline(block.text), doc);
      fragment.appendChild(element);
    }
    container.replaceChildren(fragment);
    return container;
  }

  function inlinePlain(tokens) {
    return tokens.map(t => {
      if (t.type === 'break') return '\n';
      if (t.type === 'text' || t.type === 'code' || t.type === 'link') return t.text;
      return inlinePlain(t.children || []);
    }).join('');
  }

  function toPlainText(value) {
    return parseBlocks(value).map(block => {
      if (block.type === 'rule') return '';
      if (block.type === 'code') return block.text;
      if (block.type === 'ul') return block.items.map(t => '- ' + inlinePlain(parseInline(t))).join('\n');
      if (block.type === 'ol') return block.items.map((t, i) =>
        (block.start + i) + '. ' + inlinePlain(parseInline(t))).join('\n');
      return inlinePlain(parseInline(block.text));
    }).filter(Boolean).join('\n\n');
  }

  return { parseBlocks, parseInline, render, toPlainText };
});
