"""Gera fundo/gatinhos-noite.svg e fundo/gatinhos-dia.svg a partir da lista de gatos.

Uso: python3 fundo/gerar.py [config.json] [pasta-de-saida]
     python3 fundo/gerar.py --configurar    (pergunta os gatos e grava o gatos.json)

Sem argumentos, lê gatos.json (ou gatos.exemplo.json, se você ainda não tiver o seu) da
pasta do plugin e escreve os dois SVGs em fundo/. O Panorama percebe a mudança e troca o
fundo na hora. Só SVG + CSS, sem script.
"""
import json
import os
import re
import sys
import unicodedata
from xml.sax.saxutils import escape

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Temas -------------------------------------------------------------------------------
# "preto" e "branco" mudam um pouco entre os temas para o gato não sumir no fundo.

TEMAS = {
    'noite': dict(fundo='#121015', preto='#3b3347', branco='#ece6f2', nome='#ece6f2',
                  contorno='#8a7f9a', novelo='#ff8fb1', noveloLinha='#c2577a', z='#ffb000',
                  casa='#4a3f5c', telhado='#ff8fb1', porta='#1c1822', madeira='#6b5a7d',
                  corda='#c9b79c', pote='#8ec5ff', racao='#b0763a'),
    'dia': dict(fundo='#fff6e9', preto='#2e2830', branco='#ffffff', nome='#4a2c17',
                contorno='#c9a98a', novelo='#8ec5ff', noveloLinha='#4a7fd6', z='#4a2c17',
                casa='#f0c9a0', telhado='#e8743b', porta='#4a2c17', madeira='#c9925e',
                corda='#e9d8b4', pote='#6fb7ff', racao='#8a5a2b'),
}

# --- Raças -------------------------------------------------------------------------------
# Cada raça diz a cor de cada parte. "preto"/"branco" são trocados pela cor do tema.
# Partes: pelo, listras, manchas, barriga, pernas, patas, rabo, orelhas, orelhaDentro,
# rosto (máscara do siamês), focinho, olhos, nariz.

RACAS = {
    'siames': dict(pelo='#efe3cf', pernas='#4b3428', patas='#4b3428', rabo='#4b3428',
                   orelhas='#4b3428', orelhaDentro='#6b4c3d', rosto='#4b3428',
                   olhos='#5fa8ff', nariz='#2e1f18'),
    'frajola': dict(pelo='preto', barriga='branco', patas='branco', focinho='branco',
                    orelhaDentro='#ff9db5', olhos='#c8d84a', nariz='#ff9db5'),
    'preto': dict(pelo='preto', orelhaDentro='#6a5468', olhos='#ffc233', nariz='#5a4652'),
    'branco': dict(pelo='branco', orelhaDentro='#ffc7d6', olhos='#6fb7ff', nariz='#ff9db5'),
    'cinza': dict(pelo='#8b8f9c', orelhaDentro='#e8b4c0', olhos='#ffc233', nariz='#c97b8e'),
    'laranja': dict(pelo='#f2a65a', listras='#d9802f', orelhaDentro='#ffc7d6',
                    olhos='#9bc53d', nariz='#d6336c'),
    'rajado': dict(pelo='#9a8b78', listras='#5e5144', orelhaDentro='#e8b4c0',
                   olhos='#b5c94a', nariz='#a0525e'),
    'tricolor': dict(pelo='branco', manchas=['#f2a65a', 'preto'], orelhaDentro='#ffc7d6',
                     olhos='#ffc233', nariz='#ff9db5'),
    'escaminha': dict(pelo='#3a2f2c', manchas=['#c8742c', '#8a4f22'], orelhaDentro='#8a5a4a',
                      olhos='#ffc233', nariz='#5a3a32'),
}

APELIDOS_RACA = {
    'siamesa': 'siames', 'frajolinha': 'frajola', 'tuxedo': 'frajola', 'pretinho': 'preto',
    'pretinha': 'preto', 'preta': 'preto', 'branquinho': 'branco', 'branquinha': 'branco',
    'branca': 'branco', 'cinzinha': 'cinza', 'laranjinha': 'laranja', 'rajada': 'rajado',
    'tigrado': 'rajado', 'tigrada': 'rajado', 'calico': 'tricolor', 'tartaruga': 'escaminha',
}

ATIVIDADES = {
    'andando': 'atravessa a tela',
    'brincando': 'corre atrás do novelo',
    'dormindo': 'dorme num canto',
    'sentado': 'fica sentado olhando',
    'lambendo': 'toma banho',
    'caseiro': 'dorme na casinha e sai para comer',
    'explorador': 'passeia, afia as unhas no arranhador e come',
    'brincalhao': 'corre atrás do novelo e tira uma soneca',
}
# rotina -> objetos de cenário que ela usa
ROTINAS = {'caseiro': ['casinha', 'pote'], 'explorador': ['arranhador', 'pote'], 'brincalhao': []}
APELIDOS_ATIVIDADE = {
    'andar': 'andando', 'passeando': 'andando', 'brincar': 'brincando', 'correndo': 'brincando',
    'dormir': 'dormindo', 'sentar': 'sentado', 'sentada': 'sentado', 'lamber': 'lambendo',
    'se lambendo': 'lambendo', 'tomando banho': 'lambendo', 'caseira': 'caseiro',
    'exploradora': 'explorador', 'brincalhona': 'brincalhao',
}

# chave em "cores" no gatos.json -> parte do desenho
CORES = {'pelo': 'pelo', 'listras': 'listras', 'manchas': 'manchas', 'barriga': 'barriga',
         'pernas': 'pernas', 'patas': 'patas', 'rabo': 'rabo', 'orelhas': 'orelhas',
         'orelhaDentro': 'orelhaDentro', 'rosto': 'rosto', 'focinho': 'focinho',
         'olhos': 'olhos', 'nariz': 'nariz'}

HEX = re.compile(r'^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$')


class ErroConfig(Exception):
    pass


def normaliza(texto):
    sem_acento = unicodedata.normalize('NFKD', str(texto)).encode('ascii', 'ignore').decode()
    return ' '.join(sem_acento.lower().split())


def cor_tema(cor, tema):
    return tema[cor] if cor in ('preto', 'branco') else cor


def paleta(raca, cores, tema):
    """Cores finais de um gato: a raça, as trocas do gatos.json e o tema."""
    p = dict(RACAS[raca])
    p.update(cores)
    pelo = p['pelo']
    padrao = dict(listras=None, manchas=[], barriga=None, pernas=pelo, patas=None,
                  rabo=pelo, orelhas=pelo, rosto=None, focinho=None)
    for k, v in padrao.items():
        p.setdefault(k, v)
    p['patas'] = p['patas'] or p['pernas']
    for k, v in p.items():
        if isinstance(v, list):
            p[k] = [cor_tema(c, tema) for c in v]
        elif v:
            p[k] = cor_tema(v, tema)
    p['contorno'] = tema['contorno'] if pouco_contraste(p['pelo'], tema['fundo']) else None
    return p


def luminancia(cor):
    cor = cor.lstrip('#')
    if len(cor) == 3:
        cor = ''.join(c * 2 for c in cor)
    canais = [int(cor[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canais]
    return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]


def pouco_contraste(a, b):
    la, lb = sorted((luminancia(a), luminancia(b)))
    return (lb + 0.05) / (la + 0.05) < 1.8


# --- Partes do desenho -------------------------------------------------------------------

def tracado(p, largura=2):
    return f' stroke="{p["contorno"]}" stroke-width="{largura}"' if p['contorno'] else ''


def borda(forma, p):
    """Repete a forma só com o contorno, por cima das manchas."""
    if not p['contorno']:
        return ''
    return forma.replace('/>', f' fill="none"{tracado(p)}/>')


def manchas(uid, formas_clip, p, belly, patches, stripes):
    """Barriga, manchas e listras, recortadas no formato do corpo."""
    dentro = []
    if p['barriga']:
        dentro += [f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="{p["barriga"]}"/>'
                   for x, y, rx, ry in belly]
    if p['manchas']:
        for i, (x, y, rx, ry) in enumerate(patches):
            cor = p['manchas'][i % len(p['manchas'])]
            dentro.append(f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="{cor}"/>')
    if p['listras']:
        dentro.append(f'<path d="{stripes}" stroke="{p["listras"]}" stroke-width="4" '
                      f'fill="none" stroke-linecap="round"/>')
    if not dentro:
        return ''
    return (f'<clipPath id="{uid}"> {"".join(formas_clip)} </clipPath>'
            f'<g clip-path="url(#{uid})">{"".join(dentro)}</g>')


def cabeca(uid, hx, hy, r, p, olhos='abertos'):
    """Orelhas, cabeça, rosto, olhos, nariz e bigodes, com o centro em (hx, hy)."""
    k = r / 17
    circulo = '<circle r="17"/>'
    partes = [
        f'<path d="M-12 -10 L-10 -28 L1 -15 Z M3 -15 L14 -28 L14 -8 Z" fill="{p["orelhas"]}"'
        f'{tracado(p)} stroke-linejoin="round"/>',
        f'<path d="M-9 -14 L-8 -23 L-2 -16 Z M6 -16 L11 -23 L11 -12 Z" fill="{p["orelhaDentro"]}"/>',
        f'<circle r="17" fill="{p["pelo"]}"/>',
    ]
    rosto = []
    if p['rosto']:
        rosto.append(f'<ellipse cx="1" cy="3" rx="12" ry="11" fill="{p["rosto"]}"/>')
    if p['focinho']:
        rosto.append(f'<ellipse cx="2" cy="10" rx="11" ry="7" fill="{p["focinho"]}"/>')
    if rosto:
        partes.append(f'<clipPath id="{uid}-c">{circulo}</clipPath>'
                      f'<g clip-path="url(#{uid}-c)">{"".join(rosto)}</g>')
    partes.append(borda(circulo, p))
    if olhos == 'abertos':
        partes.append(
            '<g class="blink">'
            f'<ellipse cx="-5" cy="-2" rx="2.8" ry="3.8" fill="{p["olhos"]}"/>'
            f'<ellipse cx="7" cy="-2" rx="2.8" ry="3.8" fill="{p["olhos"]}"/>'
            '<ellipse cx="-5" cy="-2" rx="1" ry="3" fill="#1a1418"/>'
            '<ellipse cx="7" cy="-2" rx="1" ry="3" fill="#1a1418"/></g>')
    else:
        escuro = p['rosto'] or p['pelo']
        traco = '#f5ead8' if luminancia(escuro) < 0.08 else '#2e1f18'
        partes.append(f'<path d="M-8 0 q4 3 8 0 M4 0 q4 3 8 0" stroke="{traco}" stroke-width="2" '
                      'fill="none" stroke-linecap="round"/>')
    partes.append(f'<path d="M0 4 l-3 -3 h6 z" fill="{p["nariz"]}"/>')
    bigode = '#f5ead8' if luminancia(p['rosto'] or p['focinho'] or p['pelo']) < 0.08 else '#7d6a5c'
    partes.append(f'<path d="M13 5 h12 M13 8 l11 3" stroke="{bigode}" stroke-width="1.4" '
                  'stroke-linecap="round" opacity=".8"/>')
    escala = f' scale({k:.3f})' if k != 1 else ''
    return f'<g transform="translate({hx} {hy}){escala}">{"".join(partes)}</g>'


def rabo(d, p, largura, classe='tail'):
    fundo = (f'<path d="{d}" fill="none" stroke="{p["contorno"]}" stroke-width="{largura + 4}" '
             'stroke-linecap="round"/>') if p['contorno'] else ''
    return (f'<g class="{classe}">{fundo}<path d="{d}" fill="none" stroke="{p["rabo"]}" '
            f'stroke-width="{largura}" stroke-linecap="round"/></g>')


def perna(x, y, alt, p, classe='', pata_em_cima=False):
    attr = f' class="{classe}"' if classe else ''
    py = y + 1 if pata_em_cima else y + alt - 10
    return (f'<g{attr}><rect x="{x}" y="{y}" width="8" height="{alt}" rx="4" fill="{p["pernas"]}"'
            f'{tracado(p)}/><rect x="{x + 1}" y="{py}" width="6" height="9" rx="3" '
            f'fill="{p["patas"]}"/></g>')


# --- Poses -------------------------------------------------------------------------------
# Cada pose devolve (svg, largura, chão, centro da cabeça em x, topo das orelhas em y),
# com o gato virado para a direita.

def andando(uid, p, comendo=False):
    corpo = '<ellipse cx="60" cy="48" rx="36" ry="18"/>'
    passo, passo_b = ('', '') if comendo else ('leg', 'leg b')
    svg = ''.join([
        rabo('M26 46 C 8 44, 2 26, 12 12', p, 7, 'tail slow' if comendo else 'tail'),
        perna(34, 56, 20, p, passo_b), perna(46, 56, 20, p, passo),
        perna(70, 56, 20, p, passo), perna(82, 56, 20, p, passo_b),
        corpo.replace('/>', f' fill="{p["pelo"]}"/>'),
        manchas(uid, [corpo], p,
                belly=[(66, 64, 30, 8), (88, 52, 9, 12)],
                patches=[(42, 40, 14, 10), (74, 52, 12, 8)],
                stripes='M44 34 q4 10 0 22 M56 31 q4 12 0 26 M68 32 q4 10 0 22'),
        borda(corpo, p),
        f'<g class="eat">{cabeca(uid, 104, 52, 17, p, olhos="fechados")}</g>' if comendo
        else cabeca(uid, 96, 32, 17, p),
    ])
    return svg, 125, 76, 96, 4


def sentado(uid, p, lambendo=False, arranhando=False):
    quadril = '<ellipse cx="40" cy="78" rx="26" ry="20"/>'
    peito = '<ellipse cx="62" cy="62" rx="20" ry="30"/>'
    pe = f'<ellipse cx="48" cy="95" rx="13" ry="4" fill="{p["patas"]}"{tracado(p)}/>'
    if lambendo:
        frente = (perna(58, 66, 32, p) +
                  f'<g class="lick-paw"><g transform="rotate(-18 74 66)">{perna(70, 36, 32, p, pata_em_cima=True)}</g></g>')
        cab = f'<g class="lick-head">{cabeca(uid, 70, 30, 17, p, olhos="fechados")}</g>'
    elif arranhando:
        # as duas patas da frente esticadas para o arranhador, que fica logo à direita
        frente = ''.join(
            f'<g class="scratch{b}"><g transform="rotate({ang} {x + 4} 66)">'
            f'{perna(x, 36, 32, p, pata_em_cima=True)}</g></g>'
            for x, ang, b in ((62, 60, ''), (70, 48, ' b')))
        cab = cabeca(uid, 68, 28, 17, p)
    else:
        frente = perna(58, 66, 32, p) + perna(70, 66, 32, p)
        cab = cabeca(uid, 68, 28, 17, p)
    svg = ''.join([
        rabo('M24 92 C 4 92, -2 72, 8 58', p, 7, 'tail slow'),
        quadril.replace('/>', f' fill="{p["pelo"]}"{tracado(p)}/>'),
        pe,
        peito.replace('/>', f' fill="{p["pelo"]}"/>'),
        manchas(uid, [quadril, peito], p,
                belly=[(72, 66, 10, 24)],
                patches=[(34, 74, 13, 10), (58, 46, 10, 11)],
                stripes='M28 64 q5 10 0 22 M40 60 q5 12 0 26 M54 40 q4 8 0 16'),
        borda(peito, p),
        frente,
        cab,
    ])
    return svg, 100, 98, 68, 0


def dormindo(uid, p):
    corpo = '<ellipse cx="60" cy="40" rx="58" ry="26"/>'
    svg = ''.join([
        '<g class="breathe">',
        corpo.replace('/>', f' fill="{p["pelo"]}"/>'),
        manchas(uid, [corpo], p,
                belly=[(96, 54, 16, 12)],
                patches=[(38, 30, 18, 11), (70, 48, 13, 8)],
                stripes='M28 18 q6 12 0 28 M44 15 q6 14 0 32 M60 15 q6 14 0 32'),
        borda(corpo, p),
        rabo('M10 52 C 30 74, 100 74, 116 46', p, 12, 'still'),
        f'<ellipse cx="100" cy="62" rx="10" ry="5" fill="{p["patas"]}"{tracado(p)}/>',
        cabeca(uid, 98, 30, 20, p, olhos='fechados'),
        '</g>',
    ])
    return svg, 120, 70, 98, -3


# --- Cena --------------------------------------------------------------------------------

CSS = '''
  .leg { transform-box: fill-box; transform-origin: 50% 0; animation: step .42s ease-in-out infinite alternate; }
  .leg.b { animation-delay: -.42s; }
  .run .leg { animation-duration: .26s; } .run .leg.b { animation-delay: -.26s; }
  .tail { transform-box: fill-box; transform-origin: 100% 100%; animation: wag 1.1s ease-in-out infinite alternate; }
  .tail.slow { transform-origin: 100% 100%; animation-duration: 2.6s; }
  .blink { transform-box: fill-box; transform-origin: 50% 50%; animation: blink 5s infinite; }
  .ball { transform-box: fill-box; transform-origin: 50% 50%; animation: roll .9s linear infinite; }
  .breathe { transform-box: fill-box; transform-origin: 50% 100%; animation: breathe 3.2s ease-in-out infinite; }
  .lick-head { transform-box: fill-box; transform-origin: 30% 100%; animation: lick .55s ease-in-out infinite alternate; }
  .lick-paw { animation: paw .55s ease-in-out infinite alternate; }
  .eat { animation: eat .4s ease-in-out infinite alternate; }
  .scratch { animation: scratch .3s ease-in-out infinite alternate; }
  .scratch.b { animation-delay: -.3s; }
  .z { animation: z 4.5s ease-out infinite; opacity: 0; }
  .z2 { animation-delay: 1.5s; } .z3 { animation-delay: 3s; }
  @keyframes step { from { transform: rotate(-22deg); } to { transform: rotate(22deg); } }
  @keyframes wag { from { transform: rotate(-10deg); } to { transform: rotate(14deg); } }
  @keyframes blink { 0%, 94%, 100% { transform: scaleY(1); } 97% { transform: scaleY(.1); } }
  @keyframes roll { to { transform: rotate(-360deg); } }
  @keyframes breathe { 0%, 100% { transform: scale(1, 1); } 50% { transform: scale(1.03, 1.06); } }
  @keyframes lick { from { transform: rotate(4deg); } to { transform: rotate(14deg); } }
  @keyframes eat { to { transform: translate(0, 3px); } }
  @keyframes scratch { to { transform: translate(-3px, 7px); } }
  @keyframes paw { from { transform: translate(0, 0); } to { transform: translate(0, -4px); } }
  @keyframes z { 0% { opacity: 0; transform: translate(0, 0) scale(.6); } 20% { opacity: 1; } 100% { opacity: 0; transform: translate(30px, -70px) scale(1.2); } }
  .nome { font: 700 15px Fredoka, "Comic Sans MS", "Comic Neue", sans-serif; text-anchor: middle; paint-order: stroke; stroke-width: 4px; stroke-linejoin: round; }
'''

FAIXAS_ANDAR = [690, 520, 760, 600, 450, 730, 560]
FAIXAS_BRINCAR = [610, 400, 700, 480]
DURACOES = [42, 57, 71, 49, 64, 53]
LUGARES = [(1300, 330), (300, 420), (830, 300), (1430, 600), (560, 480), (1080, 470), (150, 250),
           (700, 640), (1200, 720)]


def perspectiva(y):
    """Quem está mais embaixo na tela parece mais perto, e fica maior."""
    return 0.7 + 0.45 * (y - 440) / 360


def colocar(svg, larg, chao_pose, x, chao, s, virado):
    """Põe a pose com os pés em (x, chao); virado = olhando para a esquerda."""
    y = chao - chao_pose * s
    if virado:
        return f'<g transform="translate({x + larg * s:.1f} {y:.1f}) scale({-s:.3f} {s:.3f})">{svg}</g>'
    return f'<g transform="translate({x:.1f} {y:.1f}) scale({s:.3f})">{svg}</g>'


def rotulo(nome, x, y, tema):
    return (f'<text class="nome" x="{x:.1f}" y="{y:.1f}" fill="{tema["nome"]}" '
            f'stroke="{tema["fundo"]}">{escape(nome)}</text>')


def zzz(x, y, virado, tema):
    """Os três "z" de quem dorme, subindo a partir de (x, y)."""
    partes = []
    for j, (dx, dy, tam) in enumerate([(0, 0, 22), (8, -6, 18), (16, -12, 14)]):
        classe = 'z' + ('' if j == 0 else f' z{j + 1}')
        partes.append(f'<text class="{classe}" x="{x + (-dx if virado else dx):.1f}" y="{y + dy:.1f}" '
                      f'font-family="sans-serif" font-size="{tam}" font-weight="700" '
                      f'fill="{tema["z"]}">z</text>')
    return ''.join(partes)


def novelo(tema, girando=True):
    classe = ' class="ball"' if girando else ''
    return (f'<g transform="translate(15 61)"><g{classe}><circle r="15" fill="{tema["novelo"]}"/>'
            f'<path d="M-12 -6 q12 8 24 0 M-13 4 q13 -9 26 0 M-6 -13 q8 13 0 26" '
            f'stroke="{tema["noveloLinha"]}" stroke-width="2" fill="none"/></g></g>')


def corrida(uid, p, tema, s):
    """Gato correndo atrás do novelo, virado para a esquerda, com os pés em y = 76.
    Devolve (svg, largura, centro da cabeça em x, y do nome)."""
    svg, larg, chao_pose, hx, topo = andando(uid, p)
    gx = 40  # novelo na frente (x = 0..30), gato logo atrás, olhando para o novelo
    gato = colocar(svg, larg, chao_pose, gx, 76, s, True)
    linha = (f'<path d="M28 66 C 50 80, {gx + 20} 60, {gx + larg * s + 20:.0f} 74" '
             f'stroke="{tema["novelo"]}" stroke-width="2" fill="none"/>')
    return (f'<g class="run">{linha}{novelo(tema)}{gato}</g>', gx + larg * s + 40,
            gx + (larg - hx) * s, 76 + (topo - chao_pose) * s - 8)


# --- Cenário e rotinas -------------------------------------------------------------------
# Os objetos ficam numa linha de chão. Cada um é desenhado com a base centrada em (0, 0).

CHAO = 700
OBJETOS = {'casinha': 1290, 'pote': 820, 'arranhador': 400}  # x de cada um


def objeto(nome, tema):
    if nome == 'casinha':
        svg = (f'<rect x="-85" y="-120" width="170" height="120" rx="8" fill="{tema["casa"]}"/>'
               f'<path d="M-102 -114 L0 -190 L102 -114 Z" fill="{tema["telhado"]}" '
               f'stroke="{tema["telhado"]}" stroke-width="10" stroke-linejoin="round"/>'
               f'<path d="M-34 0 V-52 A34 34 0 0 1 34 -52 V0 Z" fill="{tema["porta"]}"/>')
    elif nome == 'pote':
        svg = (f'<path d="M-26 -14 L-20 0 H20 L26 -14 Z" fill="{tema["pote"]}"/>'
               f'<ellipse cy="-14" rx="26" ry="6" fill="{tema["racao"]}"/>')
    else:
        svg = (f'<rect x="-34" y="-8" width="68" height="8" rx="4" fill="{tema["madeira"]}"/>'
               f'<rect x="-9" y="-122" width="18" height="114" fill="{tema["corda"]}"/>'
               f'<path d="M-9 -100 l18 -8 M-9 -80 l18 -8 M-9 -60 l18 -8 M-9 -40 l18 -8 M-9 -20 l18 -8" '
               f'stroke="{tema["madeira"]}" stroke-width="2"/>'
               f'<rect x="-30" y="-132" width="60" height="12" rx="5" fill="{tema["madeira"]}"/>')
    return f'<g transform="translate({OBJETOS[nome]} {CHAO})">{svg}</g>'


def passos(rotina, s):
    """O roteiro de uma rotina: (segundos, pose, x final, virado para a esquerda).
    Sem x o gato fica onde está; sem "virado" ele olha para onde anda. A pose None é o
    gato fora da tela, voltando para o começo. O roteiro termina onde começa."""
    porta, pote, poste = OBJETOS['casinha'], OBJETOS['pote'], OBJETOS['arranhador']
    if rotina == 'caseiro':
        return [(38, 'dentro', None, False), (11, 'andando', pote + 62 * s), (12, 'comendo'),
                (9, 'lambendo'), (11, 'andando', porta)]
    if rotina == 'explorador':
        return [(13, 'andando', poste - 52 * s), (10, 'arranhando'), (10, 'andando', pote - 62 * s),
                (11, 'comendo'), (7, 'andando', 1060), (12, 'sentado'), (17, 'andando', 1750),
                (8, None, -150)]
    return [(14, 'correndo', 620), (22, 'soneca'), (19, 'correndo', 1800), (7, None, -220)]


def linha_do_tempo(roteiro):
    """Vira o roteiro em quadros: (% do ciclo, x, virado, pose) no começo de cada passo."""
    total = sum(passo[0] for passo in roteiro)
    x, virado, t, quadros = roteiro[-1][2], False, 0, []
    for seg, pose, *resto in roteiro:
        destino = resto[0] if resto and resto[0] is not None else x
        if len(resto) > 1:
            virado = resto[1]
        elif destino != x:
            virado = destino < x
        quadros.append((100 * t / total, x, virado, pose))
        t, x = t + seg, destino
    return total, quadros


def animacao(n, roteiro, y, atraso):
    """CSS da rotina do gato n: .mv anda, .vr vira o gato e .ps mostra uma pose por vez."""
    total, quadros = linha_do_tempo(roteiro)
    poses = list(dict.fromkeys(q[3] for q in quadros if q[3]))

    def quadro(nome, valores):
        fim = valores[0]
        corpo = ' '.join(f'{pct:.2f}% {{ {v} }}' for pct, v in valores)
        return f'  @keyframes {nome} {{ {corpo} 100% {{ {fim[1]} }} }}'

    css = [
        f'  .mv{n}, .vr{n}, .ps{n} {{ animation-duration: {total}s; animation-iteration-count: infinite; '
        f'animation-delay: {atraso:.0f}s; animation-timing-function: step-end; }}',
        f'  .mv{n} {{ animation-name: mv{n}; animation-timing-function: linear; }}',
        f'  .vr{n} {{ animation-name: vr{n}; }}',
        f'  .ps{n} {{ visibility: hidden; }}',
        quadro(f'mv{n}', [(pct, f'transform: translate({x:.0f}px, {y}px);') for pct, x, _, _ in quadros]),
        quadro(f'vr{n}', [(pct, f'transform: scale({-1 if virado else 1}, 1);') for pct, _, virado, _ in quadros]),
    ]
    for pose in poses:
        css.append(f'  .ps{n}.{pose} {{ animation-name: ps{n}{pose}; }}')
        css.append(quadro(f'ps{n}{pose}', [(pct, f'visibility: {"visible" if q == pose else "hidden"};')
                                           for pct, _, _, q in quadros]))
    return poses, '\n'.join(css)


def pose_rotina(pose, uid, p, tema, s):
    """Uma pose com os pés em (0, 0), olhando para a direita. Devolve (svg, y do nome)."""
    if pose == 'dentro':  # só o rabo para fora da porta da casinha
        return rabo('M-4 -8 C -26 -4, -44 -12, -48 -30', p, 7, 'tail slow') + zzz(30, -70, False, tema), -204
    if pose == 'correndo':
        svg, largura, _, y_nome = corrida(uid, p, tema, s * 0.85)
        return f'<g transform="translate({largura / 2:.1f} -76) scale(-1 1)">{svg}</g>', y_nome - 76
    if pose == 'soneca':
        svg, larg, chao_pose, hx, topo = dormindo(uid, p)
        extra = (zzz((hx - larg / 2 + 34) * s, (topo - chao_pose) * s + 10, False, tema) +
                 f'<g transform="translate({larg * s / 2 + 8:.1f} -76)">{novelo(tema, girando=False)}</g>')
    else:
        extra = ''
        if pose in ('andando', 'comendo'):
            svg, larg, chao_pose, hx, topo = andando(uid, p, comendo=pose == 'comendo')
        else:
            svg, larg, chao_pose, hx, topo = sentado(uid, p, lambendo=pose == 'lambendo',
                                                     arranhando=pose == 'arranhando')
    return (f'<g transform="translate({-larg * s / 2:.1f} {-chao_pose * s:.1f}) scale({s:.3f})">{svg}</g>'
            + extra, (topo - chao_pose) * s - 8)


def cena(gatos, mostrar_nomes, tema, objetos=()):
    estilos, fundo, frente = [CSS], [], []
    andantes = [g for g in gatos if g['faz'] == 'andando']
    brincantes = [g for g in gatos if g['faz'] == 'brincando']
    parados = [g for g in gatos if g['faz'] in ('dormindo', 'sentado', 'lambendo')]
    rotineiros = [g for g in gatos if g['faz'] in ROTINAS]

    for i, g in enumerate(parados):
        uid = f'g{g["n"]}'
        p = paleta(g['raca'], g['cores'], tema)
        x, chao = g['posicao'] or LUGARES[i % len(LUGARES)]
        s = max(0.9, perspectiva(chao)) * g['tamanho']
        virado = i % 2 == 1
        if g['faz'] == 'dormindo':
            svg, larg, chao_pose, hx, topo = dormindo(uid, p)
        else:
            svg, larg, chao_pose, hx, topo = sentado(uid, p, lambendo=g['faz'] == 'lambendo')
        hx_tela = x + (larg - hx if virado else hx) * s
        topo_tela = chao + (topo - chao_pose) * s
        partes = [colocar(svg, larg, chao_pose, x, chao, s, virado)]
        if g['faz'] == 'dormindo':
            partes.append(zzz(hx_tela + (-1 if virado else 1) * 34 * s, topo_tela + 10, virado, tema))
        if mostrar_nomes and g['nome']:
            partes.append(rotulo(g['nome'], hx_tela, topo_tela - 8, tema))
        fundo.append(''.join(partes))

    usados = {o for g in rotineiros for o in ROTINAS[g['faz']]} | set(objetos)
    fundo += [objeto(nome, tema) for nome in OBJETOS if nome in usados]

    for i, g in enumerate(andantes):
        uid = f'g{g["n"]}'
        p = paleta(g['raca'], g['cores'], tema)
        faixa = g['posicao'][1] if g['posicao'] else FAIXAS_ANDAR[i % len(FAIXAS_ANDAR)]
        s = perspectiva(faixa) * g['tamanho']
        svg, larg, chao_pose, hx, topo = andando(uid, p)
        esquerda = i % 2 == 1
        dur = DURACOES[i % len(DURACOES)] / max(g['tamanho'], 0.4) ** 0.5
        atraso = -round(dur * ((0.35 + i * 0.29) % 1))
        de, ate = (1700, -100 - larg * s) if esquerda else (-100 - larg * s, 1700)
        estilos.append(f'  .andar{g["n"]} {{ animation: andar{g["n"]} {dur:.0f}s linear infinite; '
                       f'animation-delay: {atraso}s; }}\n'
                       f'  @keyframes andar{g["n"]} {{ from {{ transform: translate({de:.0f}px, 0); }} '
                       f'to {{ transform: translate({ate:.0f}px, 0); }} }}')
        hx_rel = (larg - hx if esquerda else hx) * s
        partes = [colocar(svg, larg, chao_pose, 0, faixa, s, esquerda)]
        if mostrar_nomes and g['nome']:
            partes.append(rotulo(g['nome'], hx_rel, faixa + (topo - chao_pose) * s - 8, tema))
        frente.append(f'<g class="andar{g["n"]}">{"".join(partes)}</g>')

    for i, g in enumerate(brincantes):
        p = paleta(g['raca'], g['cores'], tema)
        faixa = g['posicao'][1] if g['posicao'] else FAIXAS_BRINCAR[i % len(FAIXAS_BRINCAR)]
        cena_, largura, hx_rel, y_nome = corrida(f'g{g["n"]}', p, tema,
                                                 perspectiva(faixa) * 0.85 * g['tamanho'])
        direita = i % 2 == 1
        if direita:
            cena_, hx_rel = f'<g transform="scale(-1 1)">{cena_}</g>', -hx_rel
        dur = 29 + 7 * i
        atraso = -((9 + i * 13) % dur)
        de, ate = (-100, 1700 + largura) if direita else (1700, -100 - largura)
        estilos.append(f'  .brincar{g["n"]} {{ animation: brincar{g["n"]} {dur}s linear infinite; '
                       f'animation-delay: {atraso}s; }}\n'
                       f'  @keyframes brincar{g["n"]} {{ from {{ transform: translate({de:.0f}px, {faixa - 76}px); }} '
                       f'to {{ transform: translate({ate:.0f}px, {faixa - 76}px); }} }}')
        partes = [cena_]
        if mostrar_nomes and g['nome']:
            partes.append(rotulo(g['nome'], hx_rel, y_nome, tema))
        frente.append(f'<g class="brincar{g["n"]}">{"".join(partes)}</g>')

    for i, g in enumerate(rotineiros):
        n = g['n']
        p = paleta(g['raca'], g['cores'], tema)
        # quem brinca corre na frente do cenário; os outros andam na linha dos objetos
        y = (800 if g['faz'] == 'brincalhao' else CHAO + 6) + 12 * i
        s = g['tamanho']
        roteiro = passos(g['faz'], s)
        total = sum(passo[0] for passo in roteiro)
        poses, css = animacao(n, roteiro, y, -round(total * ((i * 0.37) % 1)))
        estilos.append(css)
        partes = []
        for pose in poses:
            svg, y_nome = pose_rotina(pose, f'g{n}{pose}', p, tema, s)
            nome = rotulo(g['nome'], 0, y_nome, tema) if mostrar_nomes and g['nome'] else ''
            partes.append(f'<g class="ps{n} {pose}"><g class="vr{n}">{svg}</g>{nome}</g>')
        frente.append(f'<g class="mv{n}">{"".join(partes)}</g>')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1600 900" preserveAspectRatio="xMidYMid slice">
<style>
{chr(10).join(estilos)}
</style>
<g opacity=".95">
{chr(10).join(fundo)}
{chr(10).join(frente)}
</g>
</svg>
'''


# --- Configuração ------------------------------------------------------------------------

def ler_config(caminho):
    try:
        with open(caminho, encoding='utf-8') as f:
            dados = json.load(f)
    except json.JSONDecodeError as e:
        raise ErroConfig(f'{caminho} não é um JSON válido (linha {e.lineno}, coluna {e.colno}): {e.msg}')
    if not isinstance(dados, dict) or not isinstance(dados.get('gatos'), list):
        raise ErroConfig('o arquivo precisa ser um objeto com a lista "gatos": { "gatos": [ ... ] }')
    nomes = dados.get('nomes', True)
    if not isinstance(nomes, bool):
        raise ErroConfig('"nomes" precisa ser true ou false')
    objetos = dados.get('objetos', [])
    if not isinstance(objetos, list) or any(o not in OBJETOS for o in objetos):
        raise ErroConfig(f'"objetos" precisa ser uma lista com: {", ".join(OBJETOS)}')
    gatos = [ler_gato(i, g) for i, g in enumerate(dados['gatos'], 1)]
    return gatos, nomes, objetos


def ler_gato(n, g):
    if not isinstance(g, dict):
        raise ErroConfig(f'gato {n}: precisa ser um objeto, como {{ "nome": "Mingau", "raca": "siames" }}')
    nome = g.get('nome', '')
    quem = f'gato {n}' + (f' ("{nome}")' if nome else '')
    if not isinstance(nome, str):
        raise ErroConfig(f'{quem}: "nome" precisa ser um texto')

    raca = normaliza(g.get('raca', 'laranja'))
    raca = APELIDOS_RACA.get(raca, raca)
    if raca not in RACAS:
        raise ErroConfig(f'{quem}: raça "{g.get("raca")}" não existe. Use uma destas: {", ".join(RACAS)}')

    faz = normaliza(g.get('faz', 'andando'))
    faz = APELIDOS_ATIVIDADE.get(faz, faz)
    if faz not in ATIVIDADES:
        raise ErroConfig(f'{quem}: "faz": "{g.get("faz")}" não existe. Use uma destas: {", ".join(ATIVIDADES)}')

    tamanho = g.get('tamanho', 1)
    if not isinstance(tamanho, (int, float)) or isinstance(tamanho, bool) or not 0.3 <= tamanho <= 2:
        raise ErroConfig(f'{quem}: "tamanho" precisa ser um número de 0.3 a 2 (1 é o normal, 0.6 um filhote)')

    posicao = g.get('posicao')
    if posicao is not None:
        if (not isinstance(posicao, list) or len(posicao) != 2
                or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in posicao)):
            raise ErroConfig(f'{quem}: "posicao" precisa ser [x, y], com x de 0 a 1600 e y de 0 a 900')
        posicao = tuple(posicao)

    cores = g.get('cores', {})
    if not isinstance(cores, dict):
        raise ErroConfig(f'{quem}: "cores" precisa ser um objeto, como {{ "olhos": "#5fa8ff" }}')
    finais = {}
    for chave, valor in cores.items():
        if chave not in CORES:
            raise ErroConfig(f'{quem}: a cor "{chave}" não existe. Use: {", ".join(CORES)}')
        lista = valor if chave == 'manchas' else [valor]
        if chave == 'manchas' and not isinstance(valor, list):
            raise ErroConfig(f'{quem}: "manchas" precisa ser uma lista, como ["#f2a65a", "preto"]')
        for c in lista:
            if not isinstance(c, str) or not (HEX.match(c) or c in ('preto', 'branco')):
                raise ErroConfig(f'{quem}: a cor "{chave}" precisa ser como "#f2a65a" (ou "preto"/"branco")')
        finais[CORES[chave]] = valor
    return dict(n=n, nome=nome.strip(), raca=raca, faz=faz, tamanho=float(tamanho),
                posicao=posicao, cores=finais)


def curto(caminho):
    rel = os.path.relpath(caminho)
    return caminho if rel.startswith('..') else rel


def perguntar(texto, padrao=''):
    resposta = input(f'{texto}{f" [{padrao}]" if padrao else ""}: ').strip()
    return resposta or padrao


def escolher(texto, opcoes, apelidos, padrao):
    while True:
        valor = normaliza(perguntar(texto, padrao))
        valor = apelidos.get(valor, valor)
        if valor in opcoes:
            return valor
        print(f'  não conheço "{valor}". Use uma destas: {", ".join(opcoes)}')


def configurar():
    """Pergunta os gatos um por um e grava o gatos.json da pasta do plugin."""
    destino = os.path.join(RAIZ, 'gatos.json')
    try:
        if os.path.exists(destino) and normaliza(perguntar(
                f'{curto(destino)} já existe. Substituir? (s/n)', 'n')) not in ('s', 'sim'):
            sys.exit('gatinhos: nada mudou.')
        print('Raças:', ', '.join(RACAS))
        print('O que fazem:')
        for faz, descricao in ATIVIDADES.items():
            print(f'  {faz:<11} {descricao}')
        print('Deixe o nome vazio para terminar.\n')
        gatos = []
        while True:
            nome = perguntar(f'Nome do gato {len(gatos) + 1}')
            if not nome:
                break
            raca = escolher('  raça', RACAS, APELIDOS_RACA, 'laranja')
            faz = escolher('  faz', ATIVIDADES, APELIDOS_ATIVIDADE, 'andando')
            while True:
                try:
                    tamanho = float(perguntar('  tamanho (0.3 a 2)', '1').replace(',', '.'))
                    if 0.3 <= tamanho <= 2:
                        break
                except ValueError:
                    pass
                print('  use um número de 0.3 a 2 (1 é o normal, 0.6 um filhote)')
            gato = dict(nome=nome, raca=raca, faz=faz)
            if tamanho != 1:
                gato['tamanho'] = tamanho
            gatos.append(gato)
        if not gatos:
            sys.exit('gatinhos: nenhum gato, nada mudou.')
        nomes = normaliza(perguntar('Mostrar os nomes? (s/n)', 's')) in ('s', 'sim')
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit('gatinhos: cancelado, nada mudou.')
    linhas = ',\n'.join(f'    {json.dumps(g, ensure_ascii=False)}' for g in gatos)
    with open(destino, 'w', encoding='utf-8') as f:
        f.write(f'{{\n  "nomes": {json.dumps(nomes)},\n  "gatos": [\n{linhas}\n  ]\n}}\n')
    print(f'gatinhos: {len(gatos)} gato(s) gravados em {curto(destino)}')
    return destino


def main():
    if sys.argv[1:2] == ['--configurar']:
        config = configurar()
    elif len(sys.argv) > 1:
        config = sys.argv[1]
    else:
        config = os.path.join(RAIZ, 'gatos.json')
        if not os.path.exists(config):
            config = os.path.join(RAIZ, 'gatos.exemplo.json')
    saida = sys.argv[2] if len(sys.argv) > 2 else os.path.join(RAIZ, 'fundo')
    try:
        gatos, nomes, objetos = ler_config(config)
    except (ErroConfig, OSError) as e:
        sys.exit(f'gatinhos: {e}')
    for nome_tema, arquivo in (('noite', 'gatinhos-noite.svg'), ('dia', 'gatinhos-dia.svg')):
        with open(os.path.join(saida, arquivo), 'w', encoding='utf-8') as f:
            f.write(cena(gatos, nomes, TEMAS[nome_tema], objetos))
    print(f'gatinhos: {len(gatos)} gato(s) de {curto(config)} → {curto(saida)}/')
    animados = sum(g['faz'] not in ('dormindo', 'sentado', 'lambendo') for g in gatos)
    if len(gatos) > 10 or animados > 6:
        print('gatinhos: aviso: muitos gatos deixam o fundo mais pesado para a CPU.')


if __name__ == '__main__':
    main()
