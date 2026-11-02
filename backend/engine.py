import json, re
from pathlib import Path
from .model import State, decayed, predict
from .settings import CONFIG
LOW,HIGH=CONFIG["policy"]["target_success"]
TARGET=(LOW+HIGH)/2
READY=CONFIG["policy"]["prerequisite_mastery"]
ROOT=Path(__file__).resolve().parents[1]
GRAPH=json.loads((ROOT/'data/skills.json').read_text())
SKILLS={s['id']:s for s in GRAPH['skills']}
ITEMS=json.loads((ROOT/'data/exercises.json').read_text())
ITEM_MAP={i['id']:i for i in ITEMS}

def normalize(text):
    return re.sub(r'\s+',' ',text.strip().lower()).rstrip('.!?')

def check(item, answer):
    if item['type']=='writing':
        return {'correct':None,'error':None,'feedback':'Writing saved as an unscored activity. These checks cannot reliably judge unrestricted English.'}
    text=normalize(answer)
    ok=text in [normalize(a) for a in item['answers']]
    error=None if ok else item['distractors'].get(text,'unclassified')
    feedback='Correct. '+SKILLS[item['skill']]['rule'] if ok else next((e['feedback'] for e in SKILLS[item['skill']]['errors'] if e['id']==error),'That answer does not match the reviewed key. '+SKILLS[item['skill']]['rule'])
    return dict(correct=ok,error=error,feedback=feedback)

def recommend(states, now, previous=None):
    candidates=[]
    for item in ITEMS:
        if item['type']=='writing': continue
        skill=SKILLS[item['skill']]
        ready=all(decayed(states.get(k,State()),now)>=READY for k in skill['prerequisites'])
        if ready:
            prob=predict(states.get(item['skill'],State()),now,item['difficulty'])
            candidates.append((abs(prob-TARGET)+(0.15 if item['id']==previous else 0),item,prob))
    in_zone=[c for c in candidates if LOW<=c[2]<=HIGH]
    if in_zone:
        _,item,prob=min(in_zone,key=lambda x:(x[0],x[1]['id']))
    else:
        # Avoid repeatedly selecting mastered roots when all new skills are below target.
        _,item,prob=min(candidates,key=lambda x:(states.get(x[1]['skill'],State()).attempts,x[0],x[1]['id']))
    zone=LOW<=prob<=HIGH
    return item,prob, f"Predicted success {prob:.0%}; prerequisites meet the 60% teaching threshold. "+('Within the 70–85% challenge zone.' if zone else 'No eligible item is in the target zone; explore a least-practiced eligible skill to avoid getting stuck.')

def public_item(item):
    return {k:v for k,v in item.items() if k not in ('answers','distractors')}

def validate_generated(candidate):
    """An LLM can propose, but cannot create its own grading authority.

    Only a paraphrase-free match to a reviewed item can enter this baseline.
    Richer rule-verified generators can implement the same gate later.
    """
    for item in ITEMS:
        if all(candidate.get(k)==item[k] for k in ('skill','type','prompt','options')):
            return item.copy()
    raise ValueError('Generated exercise requires independent review or a deterministic rule proof.')
