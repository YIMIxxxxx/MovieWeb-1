from flask import Blueprint, render_template, request, Response
from movienest.auth import login_required
from movienest.db import get_db
import json

bp = Blueprint('movienest', __name__) #根目录/的BluePrint


@bp.route('/') #主界面/
def home():
    return render_template('home.html')


@bp.route('/box-office') #票房分析界面/box-office
@login_required
def box_office():
    return render_template('box-office.html')


@bp.route('/rating') #评分分析界面/rating
@login_required
def rating():
    return render_template('rating.html')


@bp.route('/search') #搜索页面/search
@login_required
def search():
    return render_template('search.html')

@bp.route('/listing') #榜单页面/listing
@login_required
def listing():
    return render_template('listing.html')

@bp.route('/resource', methods=['POST']) #资源获取路径/resource，用于获取各类票房信息
def hello():
    req = request.get_json()
    code = int(req['type'])
    if code == 0:
        data = count_type(req['startm'], req['endm'])
    elif code == 1:
        data = count_type_monthly(req['startm'], req['endm'])
    elif code == 2:
        data = box_type(req['startm'], req['endm'])
    elif code == 3:
        data = box_type_monthly(req['startm'], req['endm'])
    elif code == 4:
        data = rank_score(req['startm'], req['endm'])
    elif code == 5:
        data = get_model(req['startm'], req['endm'])
    elif code == 6:
        data = box_yearly(req['startm'], req['endm'])
    elif code == 7:
        data = get_listing(req['startm'], req['endm'], req['mtype'])
    elif code == 8:
        data = search_db(req['stype'], req['keyword'])
    return Response(json.dumps(data))


def count_type(start, end): #按类型计数，弃用
    result = {}
    db = get_db()
    for each_movie in db.execute(
            'SELECT type FROM movies WHERE'
            '? <= substr(date, 1, 7) AND substr(date, 1, 7) <= ?',
            (start, end)).fetchall():
        for each_type in json.loads(each_movie['type']):
            result.setdefault(each_type, 0)
            result[each_type] += 1
    try:
        result.pop('None')
    except:
        pass

    for each in tuple(result.keys()):
        if result[each] <= 3:
            result.pop(each)
    return result


def count_type_monthly(start, end): #按类型分类按月计数，弃用
    result = {}
    unique_date = set()
    db = get_db()
    for each_movie in db.execute(
            'SELECT type, substr(date, 1, 7) FROM movies WHERE'
            '? <= substr(date, 1, 7) AND substr(date, 1, 7) <= ?',
            (start, end)).fetchall():
        for each_type in json.loads(each_movie['type']):
            date = each_movie['substr(date, 1, 7)']
            unique_date.add(date)
            result.setdefault(each_type, {})
            result[each_type].setdefault(date, 0)
            result[each_type][date] += 1
    try:
        result.pop('None')
    except:
        pass
    
    unique_date = list(unique_date)
    unique_date.sort()
    for tp, count in result.items():
        result[tp] = []
        for date in unique_date:
            result[tp].append(count.get(date, 0))

    top_five = sorted(result.items(), key=lambda d: sum(d[1]), reverse=True)
    top_five = dict(top_five[:5])

    return unique_date, top_five


def box_type(start, end): #票房分类统计
    result = []
    db = get_db()
    for each in db.execute(
            'SELECT t.name, sum(box_office) value '
            'FROM movie_type mt '
            'JOIN movies m ON m.id = mt.movie_id '
            'JOIN types t ON t.id = mt.type_id '
            'WHERE ? <= substr(date, 1, 7) AND substr(date, 1, 7) <= ? '
            'GROUP BY t.name '
            'ORDER BY value DESC '
            'LIMIT 25',
            (start, end)).fetchall():
        result.append(tuple(each))
    return result


def box_type_monthly(start, end): #票房分类按月统计
    db = get_db()
    unique_date = db.execute(
        'SELECT DISTINCT substr(date, 1, 7)'
        'FROM movies '
        'WHERE ? <= substr(date, 1, 7) AND substr(date, 1, 7) <= ? '
        'ORDER BY date',
        (start, end)).fetchall()
    mtype = db.execute(
        'SELECT DISTINCT t.name '
        'FROM movie_type mt '
        'JOIN movies m ON m.id = mt.movie_id '
        'JOIN types t ON t.id = mt.type_id '
        'WHERE ? <= substr(date, 1, 7) AND substr(date, 1, 7) <= ? '
        'LIMIT 5',
        (start, end)).fetchall()
    unique_date = [x[0] for x in unique_date]
    result = {}
    for tp, *other in mtype:
        result.setdefault(tp, list())
        for month in unique_date:
            value = db.execute(
                'SELECT sum(box_office) value '
                'FROM movie_type mt '
                'JOIN movies m ON m.id = mt.movie_id '
                'JOIN types t ON t.id = mt.type_id '
                'WHERE substr(date, 1, 7) = ? AND t.name = ? ',
                (month, tp)).fetchone()['value']
            if value is None:
                value = 0
            result[tp].append(value)
    return unique_date, result

def box_yearly(start, end, mtype=None): #票房年同比
    db = get_db()
    unique_year = db.execute(
        'SELECT DISTINCT substr(date, 1, 4)'
        'FROM movies '
        'WHERE ? <= substr(date, 1, 4) AND substr(date, 1, 4) <= ? '
        'ORDER BY date',
        (start, end)).fetchall()
    unique_year = [x[0] for x in unique_year]
    result = {}
    for year in unique_year:
        result[year] = list()
        for i in range(1, 13):
            month = '{}-{:02d}'.format(year, i)
            if mtype is not None:
                result[year].append(db.execute(
                    'SELECT sum(box_office) value '
                    'FROM movie_type mt'
                    'JOIN movies m ON m.id = mt.movie_id '
                    'JOIN types t ON t.id = mt.type_id '
                    'WHERE substr(date, 1, 7) = ? AND t.name = ? ',
                    (month, mtype)).fetchone()['value'])
            else:
                result[year].append(db.execute(
                    'SELECT sum(box_office) value '
                    'FROM movies '
                    'WHERE substr(date, 1, 7) = ?',
                    (month, )).fetchone()['value'])
    return [i for i in range(1, 13)], result


def rank_score(start, end): #评分排序
    db = get_db()
    result = []
    for each in db.execute(
            'SELECT name, score FROM movies WHERE'
            '? <= substr(date, 1, 7) AND substr(date, 1, 7) <= ? '
            'ORDER BY score DESC '
            'LIMIT 10',
            (start, end)).fetchall():
        result.append(tuple(each))
    return result


def get_model(start, end): #获取劳模演员
    db = get_db()
    result = []
    for each in db.execute(
            'SELECT a.name, count(*) times '
            'FROM movie_actor ma '
            'JOIN movies m ON m.id = ma.movie_id '
            'JOIN actors a ON a.id = ma.actor_id '
            'WHERE ? <= substr(date, 1, 7) AND substr(date, 1, 7) <= ? '
            'GROUP BY actor_id '
            'ORDER BY times DESC '
            'LIMIT 15',
            (start, end)).fetchall():
        if each['times'] < 2:
            break
        result.append(tuple(each))
    return result

def get_listing(start, end, mtype=None): #获取榜单，如果给定mtype则说明指定类型，否则为所有类型
    db = get_db()
    result = []
    if mtype is None:
        movies = db.execute(
                'SELECT id, name, date, score FROM movies '
                'WHERE ? <= substr(date, 1, 7) AND substr(date, 1, 7) <= ? '
                'ORDER BY score DESC '
                'LIMIT 50',
                (start, end)).fetchall()
    else:
        movies = db.execute(
                'SELECT m.id id, m.name name, date, score '
                'FROM movie_type mt '
                'JOIN movies m ON m.id = mt.movie_id '
                'JOIN types t ON t.id = mt.type_id '
                'WHERE ? <= substr(date, 1, 7) AND substr(date, 1, 7) <= ? AND t.name = ? '
                'ORDER BY score DESC '
                'LIMIT 50',
                (start, end, mtype)).fetchall()
    for each in movies:
        actors = db.execute(
                'SELECT a.name '
                'FROM movie_actor ma '
                'JOIN actors a ON ma.actor_id = a.id '
                'WHERE movie_id = ?',
                (each['id'], )).fetchall()
        gen = (a[0] for a in actors)
        actors = ', '.join(gen)
        types = db.execute(
                'SELECT t.name '
                'FROM movie_type mt '
                'JOIN types t ON mt.type_id = t.id '
                'WHERE movie_id = ?',
                (each['id'], )).fetchall()
        gen = (a[0] for a in types)
        types = ', '.join(gen)
        result.append({
            'name': each['name'],
            'date': each['date'],
            'score': each['score'],
            'actors': actors,
            'types': types
            })
    return result

def search_db(stype, keyword): #搜索有关stype（电影名、导演等）的关键字相关电影
    db = get_db()
    keyword = '%{}%'.format(keyword)
    if stype == 'name':
        movies = db.execute(
                'SELECT DISTINCT id, name, date, score FROM movies '
                'WHERE name LIKE ? '
                'ORDER BY score DESC '
                'LIMIT 100',
                (keyword, )).fetchall()
    elif stype == 'director':
        movies = db.execute(
                'SELECT DISTINCT id, name, date, score FROM movies '
                'WHERE director LIKE ? '
                'ORDER BY score DESC '
                'LIMIT 100',
                (keyword, )).fetchall()
    elif stype == 'actor':
        movies = db.execute(
                'SELECT DISTINCT m.id id, m.name name, date, score '
                'FROM movie_actor ma '
                'JOIN movies m ON m.id = ma.movie_id '
                'JOIN actors a ON ma.actor_id = a.id '
                'WHERE a.name LIKE ? '
                'ORDER BY score DESC '
                'LIMIT 100',
                (keyword, )).fetchall()
    result = []
    for each in movies:
        actors = db.execute(
                'SELECT a.name '
                'FROM movie_actor ma '
                'JOIN actors a ON ma.actor_id = a.id '
                'WHERE movie_id = ?',
                (each['id'], )).fetchall()
        gen = (a[0] for a in actors)
        actors = ', '.join(gen)
        types = db.execute(
                'SELECT t.name '
                'FROM movie_type mt '
                'JOIN types t ON mt.type_id = t.id '
                'WHERE movie_id = ?',
                (each['id'], )).fetchall()
        gen = (a[0] for a in types)
        types = ', '.join(gen)
        result.append({
            'name': each['name'],
            'date': each['date'],
            'score': each['score'],
            'actors': actors,
            'types': types
            })
    return result

