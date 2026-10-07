"""Compare frozen query-candidate rankings using complete Scopus bylines.

This module does not alter the dashboard or label retrieved articles as eligible.
The current raw retrieval comparator is reconstructed from its frozen article file.
COMPLETE responses are reused or fetched by exact EID; truncated creator fields
are never used to determine first/last authorship.
"""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

from common import ROOT, as_list, digest, now, read_csv, write_csv, write_json
import design_audit as audit
from run import parse_entry
import scopus

VERSION = "query_rankings_2026_09_10"
PRIVATE = ROOT / "private" / VERSION
RESULTS = ROOT / "results" / VERSION
MEMBERS = ROOT / "results/proximity_specific_2026_09_10/membership.csv"
VARIANTS = ("current_raw", "original_query", "narrower_query")
FOCAL = {"50061672800": "Gordon Pennycook", "7003917566": "Jennifer A. Richeson",
         "15520639300": "Kurt Gray", "22986966200": "Jay J. Van Bavel"}
PUBLIC_ARTICLE_FIELDS = ["identity", "scopus_id", "all_scopus_ids", "metadata_scopus_id", "doi", "title", "year", "journal", "source_id",
    "authids", "first_authid", "last_authid", "byline_complete", "n_authors", "byline_issue", "metadata_source", "metadata_retrieved_at",
    "current_raw", "original_query", "narrower_query", "current_published_credited", "current_local_phrase_verified"]


def freeze():
    paths = [MEMBERS, ROOT/"private/articles.csv", ROOT/"results/flow_counts.json", ROOT/"results/article_metadata.csv",
             ROOT/"results/ranking_provisional.csv", ROOT/"results/top100_provisional.csv", ROOT/"results/top100_enriched.csv",
             ROOT/"results/venue_frame.csv", ROOT/"queries/proximity_audit_2026_09_10/targeted.txt",
             ROOT/"queries/proximity_specific_2026_09_10/primary_plus_specific.txt"]
    protocol = {"version": VERSION, "inputs": {str(p.relative_to(ROOT)): digest(p.read_bytes()) for p in paths},
        "counting": "One canonical article per distinct first/last Scopus author ID; sole author once. Complete ordered bylines with declared author-count agreement are required.",
        "identity": "Frozen normalized DOI identity, with Scopus-ID fallback; reconcile old-retrieval aliases by DOI or exact Scopus ID. Never merge author IDs by names.",
        "sorting": "Descending article count, then ascending numeric Scopus author ID for display only; tied scores share competition rank. Show exact top100 and all authors tied at its cutoff.",
        "status": "Raw query-candidate rankings, not validated survey-experiment output, seniority or data ownership.",
        "current_comparator": "Both actual published ranking and reconstructed 7302-article raw retrieval; published ranking additionally required local phrase verification and complete bylines.",
        "ranking_replaced": False, "manual_byline_corrections_applied": False}
    path = RESULTS/"protocol.json"
    if path.exists():
        old = json.loads(path.read_text())
        if {k:v for k,v in old.items() if k!="frozen_at"} != protocol:
            raise ValueError("Frozen ranking inputs or protocol changed")
    else:
        write_json(path, {"frozen_at": now(), **protocol})
    return protocol


def article_membership():
    frame = audit.frame_ids()
    members = {}
    for r in read_csv(MEMBERS):
        if r["targeted"] != "true":
            continue
        members[r["identity"]] = {**r, "original_query": "true", "narrower_query": r["primary_plus_specific"], "current_raw": "false"}
    bysid = {sid:k for k,r in members.items() for sid in r["all_scopus_ids"].split("|")}
    local = {r["scopus_id"]:r for r in read_csv(ROOT/"results/article_metadata.csv")}
    credited = {sid for r in read_csv(ROOT/"results/ranking_provisional.csv") for sid in r["article_ids"].split("|")}
    old_groups = defaultdict(list)
    old_rows = [r for r in read_csv(ROOT/"private/articles.csv") if r["source_id"] in frame and 2010 <= int(r["year"]) <= 2026]
    for r in old_rows:
        key = "doi:"+audit.normalize_doi(r["doi"]) if r["doi"] else "SCOPUS_ID:"+r["scopus_id"]
        old_groups[key].append(r)
    if len(old_groups) != 7302 or len(old_rows) != 7305:
        raise ValueError("Current raw retrieval does not reproduce frozen 7305/7302 accounting")
    for key, group in old_groups.items():
        candidates = {bysid[r["scopus_id"]] for r in group if r["scopus_id"] in bysid}
        if key in members:
            candidates.add(key)
        if len(candidates)>1:
            raise ValueError("Old/new DOI identity conflict")
        chosen_key = next(iter(candidates)) if candidates else key
        if chosen_key not in members:
            r = sorted(group, key=lambda r:(r["byline_complete"]!="true", not r["abstract"], int(r["scopus_id"])))[0]
            members[chosen_key] = {k:r[k] for k in ["scopus_id", "doi", "title", "year", "journal", "source_id"]} | {
                "identity":chosen_key, "all_scopus_ids":"|".join(sorted({r["scopus_id"] for r in group},key=int)),
                "original_query":"false", "narrower_query":"false", "current_raw":"true"}
        m=members[chosen_key];m["current_raw"]="true"
        m["all_scopus_ids"]="|".join(sorted(set(m["all_scopus_ids"].split("|")) | {r["scopus_id"] for r in group},key=int))
    for r in members.values():
        ids=r["all_scopus_ids"].split("|")
        r["current_published_credited"] = str(bool(set(ids)&credited)).lower()
        states={local[s]["local_phrase_verified"] for s in ids if s in local}
        r["current_local_phrase_verified"] = "true" if "true" in states else "false" if states else ""
    out=sorted(members.values(),key=lambda r:r["identity"])
    expected={"current_raw":7302,"original_query":9675,"narrower_query":9365}
    for v,n in expected.items():
        if sum(r[v]=="true" for r in out)!=n:raise ValueError("Canonical membership count mismatch: "+v)
    write_csv(RESULTS/"article_membership.csv",out,["identity","scopus_id","all_scopus_ids","doi","title","year","journal","source_id",*VARIANTS,"current_published_credited","current_local_phrase_verified"])
    return out


def valid_byline(e):
    row,_=parse_entry(e)
    declared=e.get("author-count",{})
    if isinstance(declared,dict):
        # Search COMPLETE can report its cap as the count, even for >100 authors.
        if declared.get("@limit") and int(declared.get("$",0))>=int(declared["@limit"]):return False
        declared=declared.get("$","")
    return row["byline_complete"]=="true" and str(declared)==str(row["n_authors"]) and all(x.isdigit() and int(x)>0 for x in row["authids"].split("|"))


def collect_cached(ids):
    entries={};sources={};signatures=defaultdict(set);invalid={}
    for path in sorted((ROOT/"private/cache").glob("*/*.json")):
        saved=json.loads(path.read_text())
        if saved.get("params",{}).get("view")!="COMPLETE":continue
        for e in saved.get("body",{}).get("search-results",{}).get("entry",[]):
            sid=e.get("dc:identifier","").replace("SCOPUS_ID:","")
            if sid not in ids:continue
            if not valid_byline(e):
                invalid[sid]=e
                continue
            parsed,_=parse_entry(e);signatures[sid].add(parsed["authids"])
            source={"cache_path":str(path.relative_to(ROOT)),"retrieved_at":saved.get("retrieved_at", ""),"entry_sha256":digest(json.dumps(e,sort_keys=True))}
            score=(source["retrieved_at"], bool(parsed["abstract"]), bool(parsed["keywords"]),source["entry_sha256"])
            if sid not in entries or score>sources[sid]["score"]:
                entries[sid]=e;sources[sid]={**source,"score":score}
    conflicts={sid:sorted(v) for sid,v in signatures.items() if len(v)>1}
    return entries,sources,invalid,conflicts


def apply_full_bylines(entries,sources,invalid):
    """Use archived FULL endpoint authors only when the entire sequence validates.

    Keep the existing Search abstract and keyword text unchanged so independent
    geography packets are unaffected by a byline-only completeness correction.
    """
    completion=[]
    for path in sorted((PRIVATE/"abstract_retrieval").glob("*.json")):
        saved=json.loads(path.read_text());r=saved["body"]["abstracts-retrieval-response"]
        sid=r["coredata"]["dc:identifier"].replace("SCOPUS_ID:","")
        if sid!=path.stem:raise ValueError("FULL response identity mismatch")
        old=invalid.get(sid) or entries.get(sid)
        if old is None:continue
        original_authors=as_list(old.get("author"));authors=as_list((r.get("authors") or {}).get("author"))
        e=dict(old);e["author"]=[{"@seq":a.get("@seq",""),"authid":a.get("@auid",""),"authname":a.get("ce:indexed-name",""),
            "surname":a.get("ce:surname",""),"given-name":a.get("ce:given-name", ""),"orcid":a.get("@orcid","")} for a in authors]
        e["author-count"]={"$":str(len(authors))}
        valid=valid_byline(e)
        completion.append({"scopus_id":sid,"title":old.get("dc:title",""),"search_returned_authors":len(original_authors),"full_returned_authors":len(authors),
            "search_final_returned_authid":original_authors[-1].get("authid","") if original_authors else "",
            "full_final_returned_authid":authors[-1].get("@auid","") if authors else "",
            "full_ordered_byline_valid":str(valid).lower(),"correction_applied":str(valid).lower(),
            "source_url":saved["url"],"source_sha256":digest(path.read_bytes()),
            "note":"Complete FULL sequence replaces capped Search endpoints" if valid else "FULL remains incomplete or internally inconsistent; article uncredited"})
        if valid:
            entries[sid]=e;sources[sid]={"cache_path":str(path.relative_to(ROOT)),"retrieved_at":saved["retrieved_at"],"entry_sha256":digest(json.dumps(e,sort_keys=True)),"byline_source":"Abstract Retrieval FULL"}
    write_csv(RESULTS/"byline_completion_audit.csv",completion)
    return {r["scopus_id"] for r in completion if r["full_ordered_byline_valid"]=="true"}


def batch_fetch(ids):
    q="("+" OR ".join("EID(2-s2.0-"+sid+")" for sid in ids)+")"
    entries,manifest=scopus.search(q,view="COMPLETE",namespace=VERSION)
    found={e.get("dc:identifier","").replace("SCOPUS_ID:","") for e in entries}
    if found!=set(ids):raise ValueError("Exact-ID byline request mismatch")
    path=PRIVATE/"requests"/(digest(q)+".json")
    write_json(path,{"requested_ids":ids,"view":"COMPLETE","manifest":manifest,"entries":entries})
    return len(ids)


def enrich(workers=4,allow_network=False):
    freeze();members=article_membership();ids={sid for r in members for sid in r["all_scopus_ids"].split("|")}
    entries,sources,invalid,conflicts=collect_cached(ids)
    full_valid=apply_full_bylines(entries,sources,invalid)
    fresh_ids=set()
    for p in (PRIVATE/"requests").glob("*.json"):
        s=json.loads(p.read_text())
        if s["manifest"]["complete"]:fresh_ids.update(s["requested_ids"])
    needed=(ids-set(entries) | set(conflicts))-fresh_ids-full_valid
    write_json(PRIVATE/"enrichment_plan.json",{"n_canonical":len(members),"n_scopus_ids":len(ids),"cache_valid_ids":len(entries),"need_exact_id_refresh":sorted(needed,key=int),"cached_byline_disagreements":conflicts})
    print(f"Complete-byline enrichment: {len(entries)}/{len(ids)} IDs cached; {len(needed)} exact-ID refreshes needed",flush=True)
    if needed:
        if not allow_network:raise RuntimeError("Missing COMPLETE records; rerun enrich --allow-network")
        ordered=sorted(needed,key=int);batches=[ordered[i:i+25] for i in range(0,len(ordered),25)]
        with ThreadPoolExecutor(max_workers=workers) as pool:
            for n,f in enumerate(as_completed([pool.submit(batch_fetch,x) for x in batches]),1):
                f.result();print(f"Byline batches {n}/{len(batches)} complete",flush=True)
        entries,sources,invalid,conflicts=collect_cached(ids)
    # A fresh exact-ID snapshot supersedes older byline disagreements or invalid records.
    for path in sorted((PRIVATE/"requests").glob("*.json")):
        saved=json.loads(path.read_text())
        for e in saved["entries"]:
            sid=e["dc:identifier"].replace("SCOPUS_ID:","")
            if valid_byline(e):
                entries[sid]=e;sources[sid]={"cache_path":str(path.relative_to(ROOT)),"retrieved_at":max(saved["manifest"]["dates"]),"entry_sha256":digest(json.dumps(e,sort_keys=True))}
            else:
                entries.pop(sid,None);invalid[sid]=e
    apply_full_bylines(entries,sources,invalid)
    rows=[];names={};issues=[];raw=[]
    for m in members:
        aliases=m["all_scopus_ids"].split("|")
        matches=[sid for sid in aliases if sid in entries]
        signatures={parse_entry(entries[sid])[0]["authids"] for sid in matches}
        issue=""
        if len(signatures)>1:issue="Conflicting complete bylines across DOI aliases"
        if not matches:issue="No validated complete ordered byline after exact-ID refresh"
        r={k:m.get(k,"") for k in PUBLIC_ARTICLE_FIELDS};r.update(abstract="",keywords="",indexed_keywords="",indexed_keywords_available="false")
        if matches:
            sid=sorted(matches,key=lambda sid:(not bool(entries[sid].get("dc:description")),int(sid)))[0]
            e=entries[sid];p,authors=parse_entry(e)
            expected_doi=audit.normalize_doi(m["doi"]);actual_doi=audit.normalize_doi(p["doi"])
            if expected_doi and actual_doi and expected_doi!=actual_doi:raise ValueError("Enrichment DOI differs from frozen membership: "+sid)
            r.update({k:p[k] for k in ["abstract","keywords","authids","first_authid","last_authid","n_authors"]})
            r.update(metadata_scopus_id=sid,metadata_source=sources[sid]["cache_path"],metadata_retrieved_at=sources[sid]["retrieved_at"],byline_complete=str(not issue).lower())
            for a in authors:
                current=names.get(a["authid"])
                if current is None or int(sid)>int(current["name_source_scopus_id"]):names[a["authid"]]={**a,"name_source_scopus_id":sid}
            raw.append({"identity":m["identity"],"metadata_scopus_id":sid,"source":sources[sid],"entry":e})
        else:
            r.update(byline_complete="false",n_authors="",authids="",first_authid="",last_authid="")
            # Preserve available abstracts even when authorship cannot yet be counted.
            bad=next((invalid[sid] for sid in aliases if sid in invalid),None)
            if bad:
                p,_=parse_entry(bad);r.update(abstract=p["abstract"],keywords=p["keywords"],n_authors=p["n_authors"])
        if issue:
            r["first_authid"]=r["last_authid"]=""
            issues.append({"identity":m["identity"],"scopus_id":m["scopus_id"],"title":m["title"],"issue":issue})
        r["byline_issue"]=issue;rows.append(r)
    write_csv(PRIVATE/"articles.csv",rows)
    write_json(PRIVATE/"complete_entries.json",raw)
    write_csv(RESULTS/"articles.csv",rows,PUBLIC_ARTICLE_FIELDS)
    write_csv(RESULTS/"author_names.csv",sorted(names.values(),key=lambda r:int(r["authid"])))
    write_csv(RESULTS/"byline_issues.csv",issues,["identity","scopus_id","title","issue"])
    coverage=[]
    for variant in VARIANTS:
        part=[r for r in rows if r[variant]=="true"]
        coverage.append({"variant":variant,"candidate_articles":len(part),"complete_bylines":sum(r["byline_complete"]=="true" for r in part),
            "unresolved_bylines":sum(r["byline_complete"]!="true" for r in part),"with_abstract":sum(bool(r["abstract"]) for r in part),
            "with_author_keywords":sum(bool(r["keywords"]) for r in part),"indexed_keywords_available":False})
    write_csv(RESULTS/"byline_coverage.csv",coverage)
    write_json(RESULTS/"enrichment_manifest.json",{"generated_at":now(),"private_articles_sha256":digest((PRIVATE/"articles.csv").read_bytes()),
        "public_articles_sha256":digest((RESULTS/"articles.csv").read_bytes()),"n_canonical_articles":len(rows),"coverage":coverage,
        "n_refreshed_ids":sum(len(json.loads(p.read_text())["requested_ids"]) for p in (PRIVATE/"requests").glob("*.json")),
        "known_editor_corrections_applied":False,"byline_validation":"COMPLETE Search below its author cap or complete Abstract Retrieval FULL; declared count, sequence, distinct positive author IDs, DOI identity; source snapshot archived"})
    print(json.dumps(coverage,indent=2),flush=True)
    return rows


def candidate_rank(articles,names,variant):
    scores=defaultdict(lambda:{"articles":set(),"first":set(),"last":set(),"sole":set(),"identities":set()})
    for r in articles:
        if r[variant]!="true" or r["byline_complete"]!="true":continue
        for aid in {r["first_authid"],r["last_authid"]}:
            if not aid:raise ValueError("Empty author in a complete byline")
            s=scores[aid];s["articles"].add(r["scopus_id"]);s["identities"].add(r["identity"])
            if aid==r["first_authid"]:s["first"].add(r["identity"])
            if aid==r["last_authid"]:s["last"].add(r["identity"])
            if r["first_authid"]==r["last_authid"]:s["sole"].add(r["identity"])
    ordered=sorted(scores,key=lambda aid:(-len(scores[aid]["identities"]),int(aid)))
    frequency=Counter(len(v["identities"]) for v in scores.values());rank={};preceding=0
    for n in sorted(frequency,reverse=True):rank[n]=preceding+1;preceding+=frequency[n]
    out=[]
    for pos,aid in enumerate(ordered,1):
        s=scores[aid];n=len(s["identities"])
        if len(s["articles"])!=n:raise ValueError("Canonical identity and representative ID count differ")
        out.append({"variant":variant,"display_position":pos,"competition_rank":rank[n],"authid":aid,"name":names.get(aid,aid),
            "n_articles":n,"n_first":len(s["first"]),"n_last":len(s["last"]),"n_sole":len(s["sole"]),
            "n_first_excluding_sole":len(s["first"])-len(s["sole"]),"n_last_excluding_sole":len(s["last"])-len(s["sole"]),
            "score_tie_size":frequency[n],"article_ids":"|".join(sorted(s["articles"],key=int)),
            "scopus_author_url":"https://www.scopus.com/authid/detail.uri?authorId="+aid,"status":"unvalidated_query_candidate_articles"})
    return out


def published_rank(names):
    enriched={r["authid"]:r for r in read_csv(ROOT/"results/top100_enriched.csv")}
    out=[]
    for r in read_csv(ROOT/"results/ranking_provisional.csv"):
        out.append({"variant":"current_published","display_position":int(r["position"]),"competition_rank":int(r["score_rank"]),
            "authid":r["authid"],"name":enriched.get(r["authid"],{}).get("full_name") or names.get(r["authid"],r["name"]),
            "n_articles":int(r["n_articles"]),"n_first":int(r["n_first"]),"n_last":int(r["n_last"]),"article_ids":r["article_ids"],
            "status":"actual_frozen_dashboard_ranking"})
    return out


def tie_metrics(rows,variant):
    out=[]
    for n in [40,50,100]:
        take=rows[:n];cut=take[-1]["n_articles"]
        frequencies=Counter(r["n_articles"] for r in take)
        all_at_cut=[r for r in rows if r["n_articles"]==cut]
        out.append({"variant":variant,"top_n":n,"ranked_authors":len(rows),"cutoff_count":cut,
            "distinct_scores_in_display_top_n":len(frequencies),"authors_in_tied_scores_in_display_top_n":sum(v for v in frequencies.values() if v>1),
            "tied_pairs_in_display_top_n":sum(v*(v-1)//2 for v in frequencies.values()),"adjacent_score_ties_in_display_top_n":len(take)-len(frequencies),
            "global_authors_at_cutoff":len(all_at_cut),"authors_above_cutoff":sum(r["n_articles"]>cut for r in rows),
            "top_n_including_cutoff_ties":sum(r["n_articles"]>=cut for r in rows),"cutoff_tie_display_slots":sum(r["n_articles"]==cut for r in take)})
    return out


def rank():
    freeze()
    articles=read_csv(PRIVATE/"articles.csv")
    manifest=json.loads((RESULTS/"enrichment_manifest.json").read_text())
    if manifest["private_articles_sha256"]!=digest((PRIVATE/"articles.csv").read_bytes()):raise ValueError("Article enrichment changed without manifest")
    names={r["authid"]:r["name"] for r in read_csv(RESULTS/"author_names.csv")}
    for r in read_csv(ROOT/"results/top100_enriched.csv"):
        if r.get("full_name"):names[r["authid"]]=r["full_name"]
    names.update(FOCAL)
    rankings={v:candidate_rank(articles,names,v) for v in VARIANTS}
    rankings["current_published"]=published_rank(names)
    metrics=[]
    for v,rows in rankings.items():
        write_csv(RESULTS/(v+"_ranking.csv"),rows)
        write_csv(RESULTS/(v+"_top100.csv"),rows[:100])
        cutoff=rows[99]["n_articles"]
        write_csv(RESULTS/(v+"_top100_with_cutoff_ties.csv"),[r for r in rows if r["n_articles"]>=cutoff])
        write_csv(RESULTS/(v+"_cutoff_ties.csv"),[r for r in rows if r["n_articles"]==cutoff])
        metrics.extend(tie_metrics(rows,v))
    write_csv(RESULTS/"tie_metrics.csv",metrics)
    indexes={v:{r["authid"]:r for r in rows} for v,rows in rankings.items()}
    comparison=[]
    for aid in sorted(set().union(*(set(x) for x in indexes.values())) | set(FOCAL),key=int):
        r={"authid":aid,"name":names.get(aid,aid)}
        for v in rankings:
            x=indexes[v].get(aid,{})
            r.update({v+"_"+k:x.get(k,0 if k=="n_articles" else "") for k in ["n_articles","competition_rank","display_position"]})
            r[v+"_top100"]=str(bool(x and x["display_position"]<=100)).lower()
            r[v+"_top100_including_ties"]=str(bool(x and x["n_articles"]>=rankings[v][99]["n_articles"])).lower()
        r["original_minus_current_raw_count"]=r["original_query_n_articles"]-r["current_raw_n_articles"]
        r["narrower_minus_original_count"]=r["narrower_query_n_articles"]-r["original_query_n_articles"]
        r["current_raw_minus_published_count"]=r["current_raw_n_articles"]-r["current_published_n_articles"]
        comparison.append(r)
    write_csv(RESULTS/"author_rank_comparison.csv",comparison)
    # Separate the old local-filter effect from subsequent byline enrichment.
    from analyse import deduplicate
    frozen_frame=audit.frame_ids()
    oldrows,_=deduplicate([r for r in read_csv(ROOT/"private/articles.csv") if r["source_id"] in frozen_frame and 2010<=int(r["year"])<=2026])
    for r in oldrows:
        r["current_raw"]="true"
        r["identity"]="doi:"+audit.normalize_doi(r["doi"]) if r["doi"] else "SCOPUS_ID:"+r["scopus_id"]
    frozen_raw={r["authid"]:r for r in candidate_rank(oldrows,names,"current_raw")}
    decomp=[]
    for aid in sorted(set(frozen_raw)|set(indexes["current_raw"])|set(indexes["current_published"]),key=int):
        published=indexes["current_published"].get(aid,{}).get("n_articles",0)
        oldraw=frozen_raw.get(aid,{}).get("n_articles",0)
        newraw=indexes["current_raw"].get(aid,{}).get("n_articles",0)
        decomp.append({"authid":aid,"name":names.get(aid,aid),"current_published_count":published,
            "current_raw_frozen_byline_count":oldraw,"current_raw_harmonized_byline_count":newraw,
            "count_difference_from_old_local_filter":oldraw-published,"count_difference_from_byline_enrichment":newraw-oldraw,
            "total_raw_minus_published":newraw-published})
    write_csv(RESULTS/"current_filter_decomposition.csv",decomp)
    changes=[];setsumm=[]
    for v in ["original_query","narrower_query"]:
        for comparator in ["current_published","current_raw"] + (["original_query"] if v=="narrower_query" else []):
            for scope in ["exact_top100","top100_with_cutoff_ties"]:
                def getset(k):
                    rr=rankings[k]
                    return {r["authid"] for r in rr if (r["display_position"]<=100 if scope=="exact_top100" else r["n_articles"]>=rr[99]["n_articles"])}
                a,b=getset(v),getset(comparator)
                setsumm.append({"variant":v,"comparator":comparator,"scope":scope,"candidate_pool_n":len(a),"comparator_pool_n":len(b),"shared":len(a&b),"entrants":len(a-b),"exits":len(b-a)})
                for action,ids in [("entrant",a-b),("exit",b-a)]:
                    for aid in sorted(ids,key=int):
                        n=indexes[v].get(aid,{});o=indexes[comparator].get(aid,{})
                        changes.append({"variant":v,"comparator":comparator,"scope":scope,"change":action,"authid":aid,"name":names.get(aid,aid),
                            "new_count":n.get("n_articles",0),"old_count":o.get("n_articles",0),"new_rank":n.get("competition_rank",""),"old_rank":o.get("competition_rank",""),
                            "new_display_position":n.get("display_position",""),"old_display_position":o.get("display_position","")})
    write_csv(RESULTS/"top100_membership_comparison.csv",setsumm)
    write_csv(RESULTS/"top100_entrants_exits.csv",changes)
    write_csv(RESULTS/"focal_author_comparison.csv",[r for r in comparison if r["authid"] in FOCAL])
    bysid={sid:r for r in articles for sid in r["all_scopus_ids"].split("|")}
    legacy_bylines={r["scopus_id"]:r for r in read_csv(ROOT/"private/articles.csv")}
    links=[]
    for v,rows in rankings.items():
        for r in rows:
            for sid in r["article_ids"].split("|"):
                a=bysid.get(sid)
                if not a:raise ValueError("Ranking article missing from harmonized article union: "+sid)
                endpoints=legacy_bylines[sid] if v=="current_published" else a
                links.append({"variant":v,"authid":r["authid"],"identity":a["identity"],"scopus_id":a["scopus_id"],"credited_scopus_id":sid,
                    "first":str(r["authid"]==endpoints["first_authid"]).lower(),"last":str(r["authid"]==endpoints["last_authid"]).lower(),"sole":str(endpoints["first_authid"]==endpoints["last_authid"]==r["authid"]).lower()})
    write_csv(RESULTS/"author_article_links.csv",links)
    fullnames=[r for r in read_csv(ROOT/"results/top100_enriched.csv")]
    write_csv(RESULTS/"existing_affiliations.csv",fullnames,["authid","full_name","institution","department","country","role","source_url","verified_on","verification_status"])
    write_json(RESULTS/"ranking_summary.json",{"generated_at":now(),"n_articles_union":len(articles),"byline_coverage":manifest["coverage"],
        "n_ranked_authors":{v:len(r) for v,r in rankings.items()},"top100_membership":setsumm,"tie_metrics":metrics,
        "focal_authors":[r for r in comparison if r["authid"] in FOCAL],"rankings_are_candidate_counts":True,"dashboard_replaced":False,
        "published_comparator_unchanged":True,"implementation_sha256":digest(open(__file__,"rb").read())})
    print(json.dumps({"ranked_authors":{v:len(r) for v,r in rankings.items()},"top100_membership":setsumm,"focal":[r for r in comparison if r["authid"] in FOCAL]},indent=2),flush=True)


def verify():
    """Check independently useful counting and provenance invariants offline."""
    freeze();articles=read_csv(PRIVATE/"articles.csv")
    assert len({r["identity"] for r in articles})==len(articles)
    assert len({r["scopus_id"] for r in articles})==len(articles)
    verified=[];rankings={}
    for v in VARIANTS:
        rr=read_csv(RESULTS/(v+"_ranking.csv"));rankings[v]={r["authid"]:int(r["n_articles"]) for r in rr}
        assert len(rankings[v])==len(rr)
        counts=[int(r["n_articles"]) for r in rr]
        assert counts==sorted(counts,reverse=True)
        frequency=Counter(counts);expected_ranks={};preceding=0
        for count in sorted(frequency,reverse=True):expected_ranks[count]=preceding+1;preceding+=frequency[count]
        for i,r in enumerate(rr,1):
            assert int(r["display_position"])==i
            assert int(r["competition_rank"])==expected_ranks[int(r["n_articles"])]
            assert len(set(r["article_ids"].split("|")))==int(r["n_articles"])
            assert int(r["n_first"])+int(r["n_last"])-int(r["n_sole"])==int(r["n_articles"])
        expected=sum(1 if r["first_authid"]==r["last_authid"] else 2 for r in articles if r[v]=="true" and r["byline_complete"]=="true")
        assert sum(counts)==expected
        full=read_csv(RESULTS/(v+"_top100_with_cutoff_ties.csv"))
        assert {r["authid"] for r in full}=={r["authid"] for r in rr if int(r["n_articles"])>=counts[99]}
        verified.append({"variant":v,"total_first_last_credits":expected,"ranked_authors":len(rr),"top100_including_ties":len(full)})
    assert all(n<=rankings["original_query"].get(aid,0) for aid,n in rankings["narrower_query"].items())
    old=read_csv(ROOT/"results/ranking_provisional.csv");saved=read_csv(RESULTS/"current_published_ranking.csv")
    assert [(r["authid"],r["n_articles"],r["article_ids"]) for r in old]==[(r["authid"],r["n_articles"],r["article_ids"]) for r in saved]
    assert {r["authid"] for r in read_csv(RESULTS/"focal_author_comparison.csv")}==set(FOCAL)
    for r in read_csv(RESULTS/"current_filter_decomposition.csv"):
        assert int(r["count_difference_from_old_local_filter"])+int(r["count_difference_from_byline_enrichment"])==int(r["total_raw_minus_published"])
    for z in json.loads((PRIVATE/"complete_entries.json").read_text()):
        assert valid_byline(z["entry"])
    write_json(RESULTS/"verification.json",{"verified_at":now(),"passed":True,"network_used":False,"checks":verified,
        "frozen_dashboard_credit_pairs_unchanged":True,"all_four_focal_authors_present":True,"narrower_scores_never_exceed_original":True,
        "canonical_uniqueness_competition_ranks_cutoff_ties_sole_credit_and_decomposition_checked":True,
        "search_author_caps_rejected_and_full_bylines_validated":True,"implementation_sha256":digest(open(__file__,"rb").read())})
    print("Ranking verification passed",flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage",choices=["freeze","enrich","rank","verify","all"])
    p.add_argument("--allow-network",action="store_true")
    p.add_argument("--workers",type=int,default=4)
    args=p.parse_args()
    if not 1<=args.workers<=8:p.error("workers must be 1–8")
    if args.stage=="freeze":freeze()
    if args.stage in ["enrich","all"]:enrich(args.workers,args.allow_network)
    if args.stage in ["rank","all"]:rank()
    if args.stage in ["verify","all"]:verify()
