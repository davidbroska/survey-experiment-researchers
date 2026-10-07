"""Post-benchmark DEVELOPMENT ablation; not an independently validated query.

Removes exactly two positive proximity pairs. Earlier queries, samples and reviews
remain immutable. Full STANDARD result sets are fetched with a fresh cache namespace.
"""
import argparse
import json
from collections import defaultdict
from common import ROOT, digest, now, read_csv, write_csv, write_json
import design_audit as audit
import proximity_audit as prior
import scopus
from run import parse_entry

VERSION = 'proximity_specific_2026_09_10'
PRIVATE = ROOT / 'private' / VERSION
RESULTS = ROOT / 'results' / VERSION
QUERIES = ROOT / 'queries' / VERSION
PREVIOUS_MEMBERS = prior.RESULTS / 'membership.csv'
CONSENSUS = ROOT / 'results/precision_benchmark_2026_09_10/article_consensus.csv'
AUTHORS = prior.PRIVATE / 'author_bibliographies/author_articles.csv'


def clause():
    reads = tuple(x for x in prior.READ_MATERIALS if x != 'passage*')
    manipulates = tuple(x for x in prior.MANIPULATED_MATERIALS if x != 'information')
    return ('TITLE-ABS-KEY(experiment*)\nAND ABS((read W/3 (' + ' OR '.join(reads)
            + ')) OR (manipulat* W/3 (' + ' OR '.join(manipulates) + ')))\n'
            + 'AND ABS(' + prior.POPULATION + ')')


def queries():
    original = (prior.QUERIES / 'targeted.txt').read_text().rstrip('\n')
    if original.count(prior.clause()) != 1:
        raise ValueError('Preceding frozen query does not contain expected grouped clause exactly once')
    return {'specific_clause': prior.wrap([clause()]),
            'primary_plus_specific': original.replace(prior.clause(), clause())}


def freeze():
    inputs = [PREVIOUS_MEMBERS, CONSENSUS, AUTHORS, ROOT/'results/venue_frame.csv', prior.QUERIES/'grouped_clause.txt', prior.QUERIES/'targeted.txt']
    protocol = {
        'version': VERSION,
        'stage': 'post_benchmark_development_only',
        'purpose': 'Positive-clause ablation removing only read W/3 passage* and manipulat* W/3 information after inspection of the 18 available full texts.',
        'removed_pairs': [['read','passage*'],['manipulat*','information']],
        'preserved': 'All nine remaining action-object pairs, literal read, experiment* gate, ABS population gate, year and document limits; no explicit exclusions or author/topic terms.',
        'evaluation': 'Complete Scopus identifier sets; then frozen 3401-journal intersection and canonical DOI deduplication. Retention of the 18 exposed full-text judgments is descriptive development evidence, NOT independent precision or recall. No new holdout was drawn.',
        'ranking_updated': False,
        'query_sha256': {k:digest(v) for k,v in queries().items()},
        'input_sha256': {str(p.relative_to(ROOT)):digest(p.read_bytes()) for p in inputs},
        'cache_namespace': VERSION,
    }
    path = RESULTS/'protocol.json'
    if path.exists():
        saved = json.loads(path.read_text())
        if {k:v for k,v in saved.items() if k != 'frozen_at'} != protocol:
            raise ValueError('Frozen development protocol/input changed')
    for name,q in queries().items():
        target = QUERIES/(name+'.txt')
        if target.exists() and target.read_text() != q+'\n': raise ValueError('Frozen query changed')
    for name,q in queries().items():
        p=QUERIES/(name+'.txt');p.parent.mkdir(parents=True,exist_ok=True);p.write_text(q+'\n')
    if not path.exists(): write_json(path, {'frozen_at':now(),**protocol})
    return protocol


def fetch():
    q=queries()['specific_clause'];path=PRIVATE/'search.json'
    if path.exists(): saved=json.loads(path.read_text())
    else:
        entries,manifest=scopus.search(q,view='STANDARD',namespace=VERSION)
        saved={'view':'STANDARD','manifest':manifest,'entries':entries};write_json(path,saved)
    if saved['view']!='STANDARD' or saved['manifest']['query']!=q or not saved['manifest']['complete']:
        raise ValueError('Mismatched/incomplete cache')
    return saved


def prior_global():
    q=(prior.QUERIES/'grouped_clause.txt').read_text().rstrip('\n')
    path=prior.PRIVATE/'searches'/(digest(json.dumps({'query':q,'view':'STANDARD'},sort_keys=True))+'.json')
    saved=json.loads(path.read_text())
    if not saved['manifest']['complete'] or saved['manifest']['query']!=q: raise ValueError('Incomplete original query snapshot')
    return saved


def summarize():
    freeze();saved=fetch();oldglobal=prior_global();frame=audit.frame_ids()
    newglobal={e['dc:identifier'].replace('SCOPUS_ID:',''):e for e in saved['entries']}
    originalglobal={e['dc:identifier'].replace('SCOPUS_ID:',''):e for e in oldglobal['entries']}
    globaldiff={'original_n':len(originalglobal),'specific_n':len(newglobal),
        'specific_only_ids':sorted(set(newglobal)-set(originalglobal)),
        'removed_ids':sorted(set(originalglobal)-set(newglobal)),
        'complete_original_manifest':oldglobal['manifest'],'complete_specific_manifest':saved['manifest'],
        'subset_verified':set(newglobal)<=set(originalglobal)}
    write_json(RESULTS/'global_set_comparison.json',globaldiff)
    if not globaldiff['subset_verified']: raise ValueError('Unexpected additions to positive subclause; inspect snapshot drift')
    rows=read_csv(PREVIOUS_MEMBERS); oldall={}
    for r in rows:
        for sid in r['all_scopus_ids'].split('|'):
            oldall[sid]={'dc:identifier':'SCOPUS_ID:'+sid,'prism:doi':r['doi'],'dc:title':r['title'],
                         'source-id':r['source_id'],'prism:publicationName':r['journal'],'prism:coverDate':r['year']+'-01-01'}
    data={'specific_clause':{s:e for s,e in newglobal.items() if e.get('source-id','') in frame}}
    for name in ['grouped_clause','previous_primary','previous_candidate','targeted']:
        data[name]={sid:oldall[sid] for r in rows if r[name]=='true' for sid in r['all_scopus_ids'].split('|')}
    data,conflicts=audit.canonicalize_snapshots(data)
    write_csv(RESULTS/'doi_identity_conflicts.csv',conflicts,['scopus_id','normalized_dois'])
    if conflicts:raise ValueError('DOI conflict')
    data['primary_plus_specific']={**data['previous_primary'],**data['specific_clause']}
    data['broad_plus_specific']={**data['previous_candidate'],**data['specific_clause']}
    sets={k:{audit.identity(e) for e in v.values()} for k,v in data.items()}
    comparisons=[]
    for name in ['specific_clause','primary_plus_specific','broad_plus_specific']:
        for old in ['grouped_clause','previous_primary','previous_candidate','targeted']:
            comparisons.append({'candidate':name,'comparator':old,'candidate_n':len(sets[name]),'comparator_n':len(sets[old]),
                'shared':len(sets[name]&sets[old]),'added':len(sets[name]-sets[old]),'lost':len(sets[old]-sets[name])})
    write_csv(RESULTS/'retrieval_comparison.csv',comparisons)
    write_csv(RESULTS/'retrieval_counts.csv',[{'variant':k,'unique_articles':len(v),'stage':'post_benchmark_development_only'} for k,v in sets.items()])
    allentries={s:e for v in data.values() for s,e in v.items()};aliases=defaultdict(list)
    for sid,e in sorted(allentries.items()):aliases[audit.identity(e)].append(sid)
    members=[]
    for identity,ids in sorted(aliases.items()):
        parsed,_=parse_entry(allentries[ids[0]])
        members.append({k:parsed[k] for k in ['scopus_id','doi','title','year','source_id','journal']}|
                       {'identity':identity,'all_scopus_ids':'|'.join(ids)}|{k:str(identity in v).lower() for k,v in sets.items()})
    write_csv(RESULTS/'membership.csv',members)
    changes=[]
    for cmp in comparisons:
        a,b=cmp['candidate'],cmp['comparator']
        for m in members:
            if m[a]!=m[b]:changes.append({'candidate':a,'comparator':b,'change':'added' if m[a]=='true' else 'lost',
                **{k:m[k] for k in ['identity','scopus_id','all_scopus_ids','doi','title','year','journal']}})
    write_csv(RESULTS/'article_set_differences.csv',changes)
    bysid={sid:m for m in members for sid in m['all_scopus_ids'].split('|')}
    bydoi={audit.normalize_doi(m['doi']):m for m in members if m['doi']}
    def member(r):return bysid.get(r['scopus_id'],bydoi.get(audit.normalize_doi(r.get('doi','')),{}))
    exposed=[]
    for r in read_csv(CONSENSUS):
        if r['review_coverage']!='double_pass':continue
        m=member(r);exposed.append({k:r[k] for k in ['benchmark_id','scopus_id','doi','title','design','parser_compatible','new_data']}|
            {k:m.get(k,'false') for k in sets}|{'status':'Post-hoc descriptive retention; exposed labels, no independent validation'})
    if len(exposed)!=18:raise ValueError('Expected the frozen 18 exposed double-pass reviews')
    write_csv(RESULTS/'exposed_benchmark_retention.csv',exposed)
    retention=[]
    for name in sets:
        for label in ['yes','no','unclear']:
            subset=[r for r in exposed if r['design']==label]
            retention.append({'variant':name,'design_label':label,'exposed_articles':len(subset),
                              'retrieved':sum(r[name]=='true' for r in subset),'not_retrieved':sum(r[name]!='true' for r in subset),
                              'interpretation':'Post-hoc exposed subset; not independent precision/recall'})
    write_csv(RESULTS/'exposed_benchmark_summary.csv',retention)
    authors=read_csv(AUTHORS);authorrows=[];authorpapers=[]
    for person in sorted({r['focal_author_name'] for r in authors}):
        for name in sets:
            selected=defaultdict(list)
            for r in authors:
                if r['focal_author_name']!=person:continue
                m=member(r)
                if m.get(name)=='true':selected[m['identity']].append(r)
            authorrows.append({'researcher':person,'variant':name,'any_author_position':len(selected),
                'first_last_candidate_articles':sum(any(r['first_or_last']=='true' and r['byline_complete']=='true' for r in group) for group in selected.values()),
                'status':'Development author-bibliography retrieval only, not confirmed experiments or recall'})
        for r in authors:
            if r['focal_author_name']!=person:continue
            m=member(r);authorpapers.append({k:r[k] for k in ['focal_author_name','scopus_id','doi','title','year','first_or_last','byline_complete']}|{k:m.get(k,'false') for k in sets})
    write_csv(RESULTS/'author_comparison.csv',authorrows);write_csv(RESULTS/'author_article_retrieval.csv',authorpapers)
    write_json(RESULTS/'retrieval_manifest.json',{'stage':'post_benchmark_development_only','complete':True,'manifest':saved['manifest'],
        'global_subset_verified':True,'global_records':len(newglobal),'in_frame_records':len(data['specific_clause']),
        'in_frame_unique':len(sets['specific_clause']),'member_sha256':digest((RESULTS/'membership.csv').read_bytes()),
        'specific_subset_of_original_in_frame':sets['specific_clause']<=sets['grouped_clause'],
        'implementation_sha256':digest(open(__file__,'rb').read())})
    if not sets['specific_clause']<=sets['grouped_clause']:raise ValueError('In-frame subset check failed')
    print(json.dumps({'global_specific':len(newglobal),'global_original':len(originalglobal),
        'in_frame_counts':{k:len(v) for k,v in sets.items()},'comparisons':comparisons,
        'benchmark':retention,'authors':authorrows},indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('command',choices=['freeze','retrieve','summarize']);args=parser.parse_args()
    if args.command=='freeze':freeze()
    else: summarize()
