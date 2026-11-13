# The Slowdash HTML panel "kl_channels" of slowtask-kl_pg_store.py: lists
# the channels with the latest values, and writes unit and description.
#
# An HTML panel cannot keep a state (no JavaScript), so the filter, the sort
# and the page are kept here, shared by all the viewers.

import html
import urllib.parse


ROWS_PER_PAGE = 50
SHOWS = { 'unfilled': 'without unit or description', 'all': 'all' }
SORTS = {
    'name': ('name', 'c.name, c.valid_from'),
    'cid': ('cid', 'c.cid'),
    'oldest': ('last ts, oldest first', 'l.ts NULLS LAST, c.cid'),
    'newest': ('last ts, newest first', 'l.ts DESC NULLS LAST, c.cid'),
}
TIME_FORMAT = 'YYYY-MM-DD HH24:MI:SS'

STYLE = """
<style>
  .kl-ch { font-size: 110%; }
  .kl-ch input, .kl-ch select { font-size: 100%; }
  .kl-ch .box { display: inline-block; margin: 0 1em 0.8em 0; padding: 0.4em 0.8em; border: 1px solid rgba(128,128,128,0.4); border-radius: 6px; }
  .kl-ch .table { display: table; border-collapse: collapse; }
  .kl-ch .row { display: table-row; }
  .kl-ch .row:nth-child(even) { background: rgba(128,128,128,0.08); }
  .kl-ch .row > * { display: table-cell; padding: 3px 8px; border-bottom: 1px solid rgba(128,128,128,0.25); vertical-align: middle; white-space: nowrap; }
  .kl-ch .head { background: rgba(128,128,128,0.2) !important; font-weight: bold; }
  .kl-ch .num { text-align: right; font-variant-numeric: tabular-nums; }
  .kl-ch .dim { opacity: 0.6; }
  .kl-ch .pages { margin-top: 0.8em; }
  .kl-ch .pages form { display: inline; }
  .kl-ch input[type=submit], .kl-ch a.button { padding: 1px 10px; border: 1px solid rgba(128,128,128,0.6); border-radius: 4px; text-decoration: none; color: inherit; background: rgba(128,128,128,0.1); cursor: pointer; }
</style>
"""

state = { 'name': '', 'show': 'unfilled', 'sort': 'name', 'page': 1 }


def setup(tasklet, get_db):
    """get_db() returns (asyncpg pool, quoted schema name)"""

    # An exception is shown in the browser ("Command Failed"); the tasklet has stop_on_error=False.

    @tasklet.mesh.export()
    async def describe_channel(cid:int, unit:str, description:str):
        # as written: an empty input is ''
        pool, schema = get_db()
        await pool.execute(f'SELECT {schema}.describe_channel($1::integer, $2::text, $3::text)', cid, unit.strip(), description.strip())
        return 'ok'

    @tasklet.mesh.export()
    async def create_channel(name:str, type:str, unit:str, description:str):
        pool, schema = get_db()
        unit, description = unit.strip(), description.strip()
        cid = await pool.fetchval(f'SELECT {schema}.create_channel($1::text, $2::text, $3::text, $4::text)', name.strip(), type, unit, description)
        # for an existing name, create_channel() returns its cid and changes nothing
        row = await pool.fetchrow(f'SELECT unit, description FROM {schema}.channels WHERE cid = $1', cid)
        if (row['unit'], row['description']) != (unit, description):
            raise Exception(f'"{name.strip()}" already exists (cid {cid}); unit and description are not changed, use Set')
        return f'cid {cid}'

    @tasklet.mesh.export()
    async def filter_channels(name:str, show:str, sort:str='name'):
        state.update(name=name.strip(), show=show if show in SHOWS else 'unfilled', sort=sort if sort in SORTS else 'name', page=1)
        return 'ok'

    @tasklet.mesh.export()
    async def show_page(page:int):
        state['page'] = max(1, page)
        return 'ok'

    @tasklet.content('config/html-kl_channels.html')
    async def channel_page():
        pool, schema = get_db()
        try:
            return await render(pool, schema)
        except Exception as e:
            return f'<p>kl_pg_store: DB error: {html.escape(str(e))}</p>'


async def render(pool, schema):
    name, show, sort = state['name'], state['show'], state['sort']
    where = f'''
        FROM {schema}.channels c LEFT JOIN {schema}.raw_latest l USING (cid)
        WHERE strpos(lower(c.name), lower($1)) > 0 AND ($2 <> 'unfilled' OR c.unit IS NULL OR c.description IS NULL)
    '''
    counts = await pool.fetchrow(f'''
        SELECT (SELECT count(*) {where}) AS matched, (SELECT count(*) FROM {schema}.channels) AS total,
          current_setting('TimeZone') AS timezone
    ''', name, show)
    matched, total, timezone = counts['matched'], counts['total'], counts['timezone']
    pages = max(1, -(-matched // ROWS_PER_PAGE))
    page = min(state['page'], pages)
    rows = await pool.fetch(f'''
        SELECT c.cid, c.name, c.type, c.unit, c.description,
          CASE WHEN c.valid_from = '-infinity' THEN NULL ELSE to_char(c.valid_from, '{TIME_FORMAT}') END AS valid_from,
          left(COALESCE(l.value::text, l.value_int::text, l.value_bool::text, l.value_text, l.value_jsonb::text), 30) AS last_value,
          to_char(l.ts, '{TIME_FORMAT}') AS last_ts, to_char(l.inserted_at, '{TIME_FORMAT}') AS last_inserted_at,
          extract(epoch FROM l.ts)::float8 AS last_epoch, l.ts < now() - interval '1 hour' AS stopped
        {where}
        ORDER BY {SORTS[sort][1]} LIMIT {ROWS_PER_PAGE} OFFSET {(page - 1) * ROWS_PER_PAGE}
    ''', name, show)

    def attr(x):
        return html.escape('' if x is None else str(x), quote=True)

    def options(choices, selected):
        return ''.join(f'<option value="{v}"{" selected" if v == selected else ""}>{label}</option>' for v, label in choices)

    def cell_input(field, value, size):
        # NULL (not described yet) is shown as a placeholder; Set writes it as ''
        placeholder = ' placeholder="unfilled"' if value is None else ''
        return f'<span><input name="{field}" value="{attr(value)}"{placeholder} size="{size}"></span>'

    types = options(((t, t) for t in ('double', 'integer', 'boolean', 'text', 'json')), 'double')
    lines = [
        STYLE,
        '<div class="kl-ch">',
        '<form class="box"><b>New channel</b>',
        '  <input name="name" placeholder="name" size="30">',
        f'  <select name="type">{types}</select>',
        '  <input name="unit" placeholder="unit" size="6">',
        '  <input name="description" placeholder="description" size="30">',
        '  <input type="submit" name="kl_pg_store.create_channel()" value="Create">',
        '</form><br>',
        '<form class="box"><b>Filter</b>',
        f'  name contains <input name="name" value="{attr(name)}" size="24">',
        f'  <select name="show">{options(SHOWS.items(), show)}</select>',
        f'  sort by <select name="sort">{options(((v, s[0]) for v, s in SORTS.items()), sort)}</select>',
        '  <input type="submit" name="kl_pg_store.filter_channels()" value="Apply">',
        '</form>',
        f'<p>Showing: {SHOWS[show]}' + (f', name contains "{attr(name)}"' if name else '')
        + f', sorted by {SORTS[sort][0]}. {matched} of {total} channels, page {page} of {pages}. Times in {attr(timezone)}.</p>',
        # a form cannot be in a table row; a form as a CSS table row instead
        '<div class="table">',
        '<div class="row head"><span class="num">cid</span><span>name</span><span>valid_from</span><span>type</span>'
        '<span>unit</span><span>description</span><span></span>'
        '<span class="num">last value</span><span>ts</span><span>inserted_at</span><span></span></div>',
    ]
    for r in rows:
        valid_from = attr(r['valid_from']) if r['valid_from'] else '<span class="dim">-&infin;</span>'
        last_value = r['last_value']
        if r['type'] == 'double' and last_value is not None:
            try:
                last_value = f'{float(last_value):.6g}'   # for display; the stored value is exact
            except ValueError:
                pass
        plot = ''
        if r['type'] in ('double', 'integer', 'boolean'):
            # the last day; up to the last value if the channel has stopped
            href = f'./slowplot.html?channel={urllib.parse.quote(r["name"])}&length=86400&grid=1x1'
            href += f'&to={int(r["last_epoch"]) + 60}&reload=0' if r['stopped'] else '&reload=60'
            plot = f'<a class="button" href="{attr(href)}" target="_blank">Plot</a>'
        lines += [
            '<form class="row">',
            f'<span class="num">{r["cid"]}<input type="hidden" name="cid" value="{r["cid"]}"></span>',
            f'<span>{attr(r["name"])}</span><span class="dim">{valid_from}</span><span>{r["type"]}</span>',
            cell_input('unit', r['unit'], 6), cell_input('description', r['description'], 36),
            '<span><input type="submit" name="kl_pg_store.describe_channel()" value="Set"></span>',
            f'<span class="num">{attr(last_value)}</span>',
            f'<span class="dim">{attr(r["last_ts"])}</span><span class="dim">{attr(r["last_inserted_at"])}</span>',
            f'<span>{plot}</span>',
            '</form>',
        ]
    lines.append('</div>')

    if pages > 1:
        links = [
            f'<b>{p}</b>' if p == page else
            f'<form><input type="hidden" name="page" value="{p}"><input type="submit" name="kl_pg_store.show_page()" value="{p}"></form>'
            for p in range(1, pages + 1)
        ]
        lines.append('<div class="pages">Page ' + ' '.join(links) + '</div>')
    lines.append('</div>')
    return '\n'.join(lines)
