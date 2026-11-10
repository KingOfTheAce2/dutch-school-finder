/* Schoolpath NL front end. All user-visible text lives in i18n/<lang>.json (see i18n/README.md). */
(function(){
'use strict';

/* ================= i18n ================= */
/* The one place that lists supported languages. Add a code here, add its meta below, add i18n/<code>.json. */
var SUPPORTED=['en'];
var LANG_META={en:{name:'English',locale:'en-GB'}};
var RTL_LANGS=['ar','he','fa','ur'];
var LS_LANG='schoolpath.lang';
var LANG='en',LOCALE='en-GB',DICT={},EN={},DICTS={},WARNED={},PRULES=null,NF0=null,NF1=null,DTF=null;

function look(obj,key){
  var p=key.split('.'),o=obj,i;
  for(i=0;i<p.length;i++){
    if(o===null||typeof o!=='object'||!Object.prototype.hasOwnProperty.call(o,p[i]))return undefined;
    o=o[p[i]];
  }
  return o;
}
function warnOnce(key,why){
  if(WARNED[key])return;WARNED[key]=1;
  if(window.console&&console.warn)console.warn('i18n: '+why+' "'+key+'"');
}
function tv(key){
  var v=look(DICT,key);
  if(v!==undefined)return v;
  v=look(EN,key);
  if(v!==undefined){if(LANG!=='en')warnOnce(key,'missing in '+LANG+', using en:');return v}
  warnOnce(key,'missing key');
  return undefined;
}
function has(key){return look(DICT,key)!==undefined||look(EN,key)!==undefined}
function plural(n){
  if(!PRULES){try{PRULES=new Intl.PluralRules(LOCALE)}catch(e){PRULES=new Intl.PluralRules('en')}}
  return PRULES.select(n);
}
function brandName(){var v=look(DICT,'brand.name');if(v===undefined)v=look(EN,'brand.name');return v||''}
function fill(s,vars){
  return s.replace(/\{(\w+)\}/g,function(m,k){
    var v=vars&&vars[k];
    if(v!==undefined&&v!==null)return typeof v==='number'?numF(v):String(v);
    if(k==='brand')return brandName();
    return m;
  });
}
/* t('key',{name:'x'}). A value of the form {one:'..',other:'..'} is a plural, chosen by vars.n */
function t(key,vars){
  var v=tv(key);
  if(v===undefined)return key;
  if(v!==null&&typeof v==='object'&&!Array.isArray(v)){
    var n=vars&&typeof vars.n==='number'?vars.n:null;
    var c=n===null?'other':plural(n);
    v=v[c]!==undefined?v[c]:v.other;
  }
  if(typeof v!=='string')return key;
  return fill(v,vars);
}
function numF(n){
  if(typeof n!=='number')return String(n);
  if(!NF0)NF0=new Intl.NumberFormat(LOCALE);
  return NF0.format(n);
}
function dec1(n){
  if(!NF1)NF1=new Intl.NumberFormat(LOCALE,{minimumFractionDigits:1,maximumFractionDigits:1});
  return NF1.format(n);
}
function fmtDate(d){
  if(!DTF)DTF=new Intl.DateTimeFormat(LOCALE,{weekday:'short',day:'numeric',month:'short',year:'numeric'});
  return DTF.format(d);
}
function fmtDay(d){return new Intl.DateTimeFormat(LOCALE,{day:'numeric',month:'long',year:'numeric'}).format(d)}
/* tiny safe markup: only <b>...</b> is turned into an element, everything else stays text */
function rich(s){
  var f=document.createDocumentFragment(),parts=String(s).split(/(<\/?b>)/),bold=null,cur=f,i,p;
  for(i=0;i<parts.length;i++){
    p=parts[i];
    if(p==='<b>'){if(!bold){bold=document.createElement('b');cur=bold}}
    else if(p==='</b>'){if(bold){f.appendChild(bold);bold=null;cur=f}}
    else if(p)cur.appendChild(document.createTextNode(p));
  }
  if(bold)f.appendChild(bold);
  return f;
}
function pickLang(){
  var c,i,q;
  try{q=new URLSearchParams(location.search).get('lang');if(q&&SUPPORTED.indexOf(q.toLowerCase())>-1)return q.toLowerCase()}catch(e){}
  try{c=localStorage.getItem(LS_LANG);if(c&&SUPPORTED.indexOf(c)>-1)return c}catch(e){}
  try{
    var nl=navigator.languages&&navigator.languages.length?navigator.languages:[navigator.language];
    for(i=0;i<nl.length;i++){
      if(!nl[i])continue;
      var code=String(nl[i]).toLowerCase().split('-')[0];
      if(SUPPORTED.indexOf(code)>-1)return code;
    }
  }catch(e){}
  return 'en';
}
function loadDict(code){
  if(DICTS[code])return Promise.resolve(DICTS[code]);
  return fetch('i18n/'+code+'.json').then(function(r){if(!r.ok)throw new Error('i18n '+code);return r.json()}).then(function(j){DICTS[code]=j;return j});
}
function setLocaleVars(code){
  LANG=code;
  LOCALE=(LANG_META[code]&&LANG_META[code].locale)||code;
  PRULES=null;NF0=null;NF1=null;DTF=null;
  document.documentElement.setAttribute('lang',code);
  document.documentElement.setAttribute('dir',RTL_LANGS.indexOf(code)>-1?'rtl':'ltr');
}

/* ================= tiny DOM helpers ================= */
function $(id){return document.getElementById(id)}
function qsa(sel,root){return Array.prototype.slice.call((root||document).querySelectorAll(sel))}
function h(tag,attrs,kids){
  var e=document.createElement(tag),k,v;
  if(attrs)for(k in attrs){v=attrs[k];if(v===null||v===undefined||v===false)continue;
    if(k==='class')e.className=v;else if(k==='text')e.textContent=v;
    else if(k.slice(0,2)==='on')e.addEventListener(k.slice(2),v);
    else e.setAttribute(k,v===true?'':v)}
  if(kids!==undefined&&kids!==null){(Array.isArray(kids)?kids:[kids]).forEach(function(c){
    if(c===null||c===undefined||c===false)return;
    e.appendChild(typeof c==='string'||typeof c==='number'?document.createTextNode(String(c)):c)})}
  return e;
}
function hr(tag,cls,str){var e=document.createElement(tag);if(cls)e.className=cls;e.appendChild(rich(str));return e}
var SVGNS='http://www.w3.org/2000/svg';
function svgEl(tag,attrs,text){
  var e=document.createElementNS(SVGNS,tag),k;
  if(attrs)for(k in attrs)e.setAttribute(k,attrs[k]);
  if(text!==undefined&&text!==null)e.textContent=text;
  return e;
}
function ico(name){
  var s=svgEl('svg',{'class':'ic','aria-hidden':'true'});
  s.appendChild(svgEl('use',{href:'#i-'+name}));
  return s;
}
function esc(s){return String(s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]})}
function clear(n){while(n.firstChild)n.removeChild(n.firstChild)}

/* ================= URLs: the only place that builds or changes a route (hash routes today) ================= */
var U={
  route:function(){return '#/'},
  routePc:function(pc){return '#/?pc='+pc},
  view:function(v,q){return v==='route'?'#/':'#/'+v+(q||'')},
  school:function(id){return '#/school/'+id},
  compare:function(ids){return '#/compare/'+ids.join(',')},
  mapFocus:function(id){return '#/map?s='+id}
};
function navigate(u){location.hash=u}
function replaceUrl(u){try{history.replaceState(null,'',u)}catch(e){}}
/* current location as {view,arg,q}; the matching builders are in U above */
function parseRoute(){
  var raw=location.hash.replace(/^#/,''),q='',i=raw.indexOf('?');
  if(i>-1){q=raw.slice(i+1);raw=raw.slice(0,i)}
  var parts=raw.split('/').filter(Boolean);
  var arg=parts[1]||'';try{arg=decodeURIComponent(arg)}catch(e){}
  return {view:parts[0]||'route',arg:arg,q:q};
}
/* data-route="find" links get their href from U, so no markup hard-codes a URL */
function applyRoutes(){qsa('[data-route]').forEach(function(a){a.setAttribute('href',U.view(a.getAttribute('data-route')))})}

/* ================= sources: titles in i18n (src.*), links here ================= */
var SRC_URL={
  basis:'https://www.rijksoverheid.nl/documenten/vraag-en-antwoord/basisonderwijs/basisschool-kiezen-voor-kind',
  wanneer:'https://www.rijksoverheid.nl/themas/onderwijs/basisonderwijs/vraag-en-antwoord/basisonderwijs/wanneer-mag-mijn-kind-naar-de-basisschool',
  blijven:'https://www.rijksoverheid.nl/themas/onderwijs/basisonderwijs/vraag-en-antwoord/basisonderwijs/wie-bepaalt-of-mijn-kind-blijft-zitten-of-overgaat-naar-de-volgende-klas',
  tijdlijn:'https://www.rijksoverheid.nl/onderwerpen/schooladvies-en-doorstroomtoets-basisschool/tijdlijn-schooladvies-2027',
  advies:'https://www.rijksoverheid.nl/themas/onderwijs/schooladvies-en-doorstroomtoets-basisschool/toelating-voortgezet-onderwijs-gebaseerd-op-definitief-schooladvies',
  voraad:'https://vo-raad.nl/nieuws/data-2026-2027-rondom-doorstroomtoets-en-aanmelding-in-het-vo',
  inschr:'https://www.rijksoverheid.nl/themas/onderwijs/voortgezet-onderwijs/vraag-en-antwoord/voortgezet-onderwijs/inschrijven-voortgezet-onderwijs',
  weiger:'https://www.rijksoverheid.nl/themas/onderwijs/voortgezet-onderwijs/vraag-en-antwoord/voortgezet-onderwijs/weigeren-kind-voortgezet-onderwijs',
  vmbo:'https://www.rijksoverheid.nl/themas/onderwijs/voortgezet-onderwijs/vraag-en-antwoord/voortgezet-onderwijs/hoe-zit-het-vmbo-in-elkaar',
  havo:'https://www.rijksoverheid.nl/themas/onderwijs/voortgezet-onderwijs/vraag-en-antwoord/voortgezet-onderwijs/hoe-zit-de-havo-in-elkaar',
  vwo:'https://www.rijksoverheid.nl/themas/onderwijs/voortgezet-onderwijs/vraag-en-antwoord/voortgezet-onderwijs/hoe-zit-het-vwo-in-elkaar',
  pro:'https://www.rijksoverheid.nl/themas/onderwijs/voortgezet-onderwijs/vraag-en-antwoord/voortgezet-onderwijs/hoe-lang-mogen-leerlingen-doen-over-het-voortgezet-onderwijs',
  brug:'https://www.vo-raad.nl/nieuws/factsheet-brede-brugklas-vergroot-kansen-leerlingen',
  loket:'https://onderwijsloket.com/kennisbank/artikelen/hoe-zit-het-nederlandse-onderwijssysteem-in-elkaar',
  schema:'https://www.nuffic.nl/onderwijssystemen/nederland/schema-onderwijssysteem-nederland',
  nuf:'https://www.nuffic.nl/en/education-systems/netherlands',
  nufMbo:'https://www.nuffic.nl/en/education-systems/the-netherlands/secondary-vocational-education',
  kiesmbo:'https://www.kiesmbo.nl/over-het-mbo/vooropleiding-en-toelating',
  kiesEntree:'https://www.kiesmbo.nl/over-het-mbo/entreeopleiding',
  mboRijks:'https://www.rijksoverheid.nl/themas/onderwijs/middelbaar-beroepsonderwijs/vraag-en-antwoord/middelbaar-beroepsonderwijs/uit-welke-mbo-opleidingen-kan-ik-kiezen',
  mboToel:'https://www.rijksoverheid.nl/themas/onderwijs/middelbaar-beroepsonderwijs/vraag-en-antwoord/middelbaar-beroepsonderwijs/wat-zijn-de-toelatingseisen-voor-het-mbo',
  mboraad:'https://www.mboraad.nl/het-mbo/soorten-onderwijs/middelbaar-beroepsonderwijs-mbo',
  gov:'https://www.government.nl/topics/secondary-vocational-education-mbo-and-tertiary-higher-education/tertiary-higher-education',
  sk123:'https://www.studiekeuze123.nl/wat-ga-jij-kiezen/artikel/hoe-is-het-hoger-onderwijs-opgebouwd',
  sk21:'https://www.studiekeuze123.nl/studiekeuzewoordenboek/21-toelatingsonderzoek',
  nieuw:'https://www.rijksoverheid.nl/onderwerpen/basisonderwijs/onderwijs-voor-nieuwkomers',
  sio:'https://www.sio.nl/',
  oco:'https://ocoamsterdam.nl/',
  vo_raad_moving_from_vmbo_to_havo_and_fro:'https://vo-raad.nl/onderwerpen/overgang-vmbo-havo-havo-vwo/wat-speelt-er',
  rijksoverheid_what_is_tto:'https://www.rijksoverheid.nl/documenten/vraag-en-antwoord/onderwijs-en-internationalisering/wat-is-tweetalig-onderwijs-tto-in-het-voortgezet-onderwijs',
  dutch_international_schools:'https://www.dutchinternationalschools.nl/',
  isa_fees_2026_27:'https://www.isa.nl/fees/',
  iamexpat_school_fees_third_party_guide:'https://www.iamexpat.nl/education/primary-secondary-education/tuition-fees-netherlands',
  rijksoverheid_passend_onderwijs:'https://www.rijksoverheid.nl/documenten/vraag-en-antwoord/passend-onderwijs/hoe-krijgt-mijn-kind-passend-onderwijs',
  rijksoverheid_bsn_in_education:'https://www.rijksoverheid.nl/onderwerpen/privacy-en-persoonsgegevens/burgerservicenummer-bsn/bsn-in-het-onderwijs',
  rijksoverheid_leerplicht_en_kwalificatie:'https://www.rijksoverheid.nl/onderwerpen/leerplicht/leerplicht-en-kwalificatieplicht',
  rijksoverheid_compulsory_education_and_a:'https://www.rijksoverheid.nl/onderwerpen/leerplicht/vraag-en-antwoord/leerplicht-buitenlandse-school',
  rijksoverheid_leerplicht_and_school_holi:'https://www.rijksoverheid.nl/onderwerpen/leerplicht/vraag-en-antwoord/leerplicht-schoolvakanties',
  rijksoverheid_voluntary_parental_contrib:'https://www.rijksoverheid.nl/documenten/2023/09/01/documenten-vrijwillige-ouderbijdrage-po-en-vo',
  inspectie_voluntary_parental_contributio:'https://www.onderwijsinspectie.nl/binaries/onderwijsinspectie/documenten/rapporten/2023/04/20/voldoen-scholen-aan-de-wetgeving-omtrent-vrijwillige-ouderbijdrage/Voldoen+scholen+aan+de+wetgeving+omtrent+vrijwillige+ouderbijdrage-Feiten+en+reflectie.pdf',
  rijksoverheid_lunch_at_primary_school:'https://www.rijksoverheid.nl/onderwerpen/basisonderwijs/vraag-en-antwoord/kan-mijn-kind-tussen-de-middag-overblijven-op-de-basisschool',
  rijksoverheid_childcare_benefit_amounts_:'https://www.rijksoverheid.nl/themas/belastingen-uitkeringen-en-toeslagen/kinderopvangtoeslag/bedragen-kinderopvangtoeslag-2026',
  rijksoverheid_when_to_register_at_a_prim:'https://www.rijksoverheid.nl/vraag-en-antwoord/basisonderwijs/wanneer-kind-aanmelden-basisschool',
  oco_amsterdam_priority_rules_for_primary:'https://ocoamsterdam.nl/vragen/voorrangsregels-voor-plaatsen-van-kinderen-op-basisscholen-in-amsterdam',
  de_vo_gids_how_lotteries_work:'https://www.devogids.nl/stappenplan-vo-gids/hulp/hoe-werkt-loting-voor-de-middelbare-school/',
  samen_naar_het_vo_utrecht_2026:'https://www.samennaarhetvo.nl/aktueel/persbericht-2026/',
  bovo_haaglanden_results_2026:'https://www.bovohaaglanden.nl/uitslag-aanmeldingen-middelbare-school-haaglanden-2026/',
  rijksoverheid_passend_onderwijs2:'https://www.rijksoverheid.nl/onderwerpen/passend-onderwijs',
  rijksoverheid_public_and_special_educati:'https://www.rijksoverheid.nl/themas/onderwijs/vrijheid-van-onderwijs/openbaar-en-bijzonder-onderwijs',
  belastingdienst_content_of_the_expat_sch:'https://www.belastingdienst.nl/wps/wcm/connect/bldcontentnl/belastingdienst/zakelijk/internationaal/personeel/u_bent_niet_in_nederland_gevestigd_loonheffingen_inhouden/als_u_loonheffingen_gaat_inhouden/extraterritoriale_kosten_en_de_30procentregeling/inhoud_van_de_regeling/inhoud_van_de_regeling',
  business_gov_nl_30_ruling_down_to_27:'https://business.gov.nl/amendments/30-percent-ruling-compensation-down-to-27-percent/',
  nuffic_applying_for_a_credential_evaluat:'https://www.nuffic.nl/en/study-and-work-in-the-netherlands/applying-for-a-credential-evaluation',
  study_in_nl_checking_your_diploma:'https://www.studyinnl.org/plan-your-stay/checking-your-diploma',
  study_in_nl:'https://www.studyinnl.org/',
  rijksoverheid_which_diplomas_give_access:'https://www.rijksoverheid.nl/documenten/vraag-en-antwoord/hoger-onderwijs/met-welke-diploma-s-kan-ik-naar-de-universiteit-of-hogeschool',
  duo_open_education_data:'https://duo.nl/open_onderwijsdata/',
  inspectie_van_het_onderwijs:'https://www.onderwijsinspectie.nl/',
  nuffic_bilingual_education:'https://www.nuffic.nl/onderwijssectoren/voortgezet-onderwijs/tweetalig-onderwijs',
  nuffic_all_tto_schools:'https://www.nuffic.nl/onderwijssectoren/voortgezet-onderwijs/tweetalig-onderwijs/alle-tto-scholen-in-nederland',
  oco_amsterdam_when_to_register:'https://ocoamsterdam.nl/vragen/wanneer-moet-ik-mijn-kind-aanmelden-voor-de-basisschool'
};
var SRC_ORDER=['schema','nuf','loket','gov','sk123','sk21','basis','wanneer','blijven','tijdlijn','advies','voraad','inschr','weiger','vmbo','havo','vwo','pro','brug','kiesmbo','kiesEntree','mboRijks','mboToel','nufMbo','mboraad','nieuw','sio','oco','vo_raad_moving_from_vmbo_to_havo_and_fro','rijksoverheid_what_is_tto','dutch_international_schools','isa_fees_2026_27','iamexpat_school_fees_third_party_guide','rijksoverheid_passend_onderwijs','rijksoverheid_bsn_in_education','rijksoverheid_leerplicht_en_kwalificatie','rijksoverheid_compulsory_education_and_a','rijksoverheid_leerplicht_and_school_holi','rijksoverheid_voluntary_parental_contrib','inspectie_voluntary_parental_contributio','rijksoverheid_lunch_at_primary_school','rijksoverheid_childcare_benefit_amounts_','rijksoverheid_when_to_register_at_a_prim','oco_amsterdam_priority_rules_for_primary','de_vo_gids_how_lotteries_work','samen_naar_het_vo_utrecht_2026','bovo_haaglanden_results_2026','rijksoverheid_passend_onderwijs2','rijksoverheid_public_and_special_educati','belastingdienst_content_of_the_expat_sch','business_gov_nl_30_ruling_down_to_27','nuffic_applying_for_a_credential_evaluat','study_in_nl_checking_your_diploma','study_in_nl','rijksoverheid_which_diplomas_give_access','duo_open_education_data','inspectie_van_het_onderwijs','nuffic_bilingual_education','nuffic_all_tto_schools','oco_amsterdam_when_to_register'];
var LAST_CHECKED='2026-11-10';
function srcLine(keys,cls){
  var p=h('p',{class:cls||'src'},[t('src.label')+' ']);
  keys.forEach(function(k,i){var u=SRC_URL[k];if(!u)return;if(i)p.appendChild(document.createTextNode(' · '));
    p.appendChild(h('a',{href:u,target:'_blank',rel:'noopener',text:t('src.'+k)}))});
  return p;
}

/* ================= state ================= */
var KEY='schoolpath.v1',KEY_OLD='schoollijn.v2',CMP_KEY='schoolpath.cmp',CMP_KEY_OLD='schoollijn.cmp';
var DEF={age:'',pc:'',level:'',grp:'',newc:false,radius:10,chips:null,example:false};
var state;
var nPo=15,nVo=15,nIsk=10,preview=false,poSboOpen=false;
var AGE_RE=/^(u4|[4-9]|1[0-8])$/;
/* a Dutch postcode is "1234 AB"; the data is by the 4 digits, so "1234", "1234AB" and "1234 ab" all work */
function parsePc(v){var m=/^\s*([1-9]\d{3})\s*([A-Za-z]{2})?\s*$/.exec(String(v==null?'':v));return m?m[1]:''}
/* move state saved under the previous name to the new keys once, so returning visitors keep their settings */
function migrateStorage(){
  try{
    var o=localStorage.getItem(KEY_OLD);
    if(o!==null){if(localStorage.getItem(KEY)===null)localStorage.setItem(KEY,o);localStorage.removeItem(KEY_OLD)}
    var c=localStorage.getItem(CMP_KEY_OLD);
    if(c!==null){if(localStorage.getItem(CMP_KEY)===null)localStorage.setItem(CMP_KEY,c);localStorage.removeItem(CMP_KEY_OLD)}
  }catch(e){}
}
function loadState(){
  var d={},k;for(k in DEF)d[k]=DEF[k];
  try{var r=localStorage.getItem(KEY);if(r){var o=JSON.parse(r);if(o&&typeof o==='object'&&!o.example){
    for(var k2 in d){if(o[k2]!==undefined&&o[k2]!==null)d[k2]=o[k2]}
    d.age=String(d.age);d.pc=String(d.pc);
    if(!AGE_RE.test(d.age))d.age='';
    if(!/^[1-9]\d{3}$/.test(d.pc))d.pc='';
    d.radius=+d.radius||10;
    if(!Array.isArray(d.chips))d.chips=null;
    d.example=false;d.newc=!!d.newc}}}catch(e){}
  return d;
}
/* an example is never saved as if it were the visitor's own data */
function save(){if(state.example)return;try{localStorage.setItem(KEY,JSON.stringify(state))}catch(e){}}
function hasInput(){return AGE_RE.test(state.age)&&/^[1-9]\d{3}$/.test(state.pc)}

/* ================= data ================= */
var DB={po:null,vo:null,pc4:null,meta:null,feat:null,status:'loading'};
function denLabel(nl){var m=tv('den');return (m&&m[nl])||t('den.other')}
function applyDen(){
  [DB.po,DB.vo].forEach(function(l){if(l)l.forEach(function(o){o.denT=denLabel(o.denNl)})});
}
function mapRows(j,extra){
  var cols=j.cols,out=new Array(j.rows.length),i,r,o,c;
  for(i=0;i<j.rows.length;i++){r=j.rows[i];o={};for(c=0;c<cols.length;c++)o[cols[c]]=r[c];
    o.denNl=j.den[o.den];o.denT=denLabel(o.denNl);
    o.latR=o.lat*Math.PI/180;o.cosL=Math.cos(o.latR);
    if(extra)extra(o);out[i]=o}
  return out;
}
var ST_BITS={PRO:1,VBO:6,MAVO:24,HAVO:32,VWO:64};
function loadData(){
  DB.status='loading';renderStatus();
  var names=['schools_po','schools_vo','pc4','meta'];
  return Promise.all(names.map(function(n){
    return fetch('data/'+n+'.json').then(function(r){if(!r.ok)throw new Error(n);return r.json()}).catch(function(){return null});
  })).then(function(a){
    DB.meta=a[3];
    if(a[0]&&a[1]&&a[2]){
      DB.po=mapRows(a[0]);
      DB.vo=mapRows(a[1],function(o){
        if(!o.tracks&&o.st){o.fb=1;var tt=String(o.st).split('/'),m=0;tt.forEach(function(x){m|=ST_BITS[x]||0});o.tracks=m}
        o.isk=/\bISK\b|schakelklas|internationale schakel/i.test(o.name)||o.st==='BRUGJAAR';
      });
      DB.pc4=a[2];DB.status='ready';
    }else{DB.status='error'}
  }).then(function(){if(DB.status==='ready')buildIndex();renderStatus();renderSources();render();loadFeatures();refreshView()});
}
/* features.json (school concepts, open days) is optional: the page works without it */
function loadFeatures(){
  if(DB.feat||DB.status!=='ready')return;
  fetch('data/features.json').then(function(r){if(!r.ok)throw new Error('features');return r.json()}).then(function(j){
    if(j&&j.schools&&typeof j.schools==='object'){DB.feat=j;renderSources();render();refreshView()}
  }).catch(function(){});
}

/* ================= school features and open days (features.json) ================= */
var FT_ORDER=['tto','ib','technasium','international','montessori','dalton','jenaplan','vrije_school','newcomer'];
var FT_FILTER_VO=['tto','ib','technasium','montessori','dalton','jenaplan','vrije_school','newcomer'];
var FT_FILTER_PO=['montessori','dalton','jenaplan','vrije_school','ib','newcomer'];
var FT_ALL=['tto','ib','technasium','international','montessori','dalton','jenaplan','vrije_school','newcomer'];
var ffVo=[],ffPo=[];
function ftLbl(k){return t('ft.'+k)}
function ftShort(k){return has('ftShort.'+k)?t('ftShort.'+k):t('ft.'+k)}
function odLabel(l,lower){var m=tv(lower?'od.labelsLower':'od.labels');return (m&&m[l])||t(lower?'od.defaultLower':'od.default')}
function featSrcName(url,kind){
  var host='';try{host=new URL(url).hostname.replace(/^www\./,'')}catch(e){}
  if(kind!=='list')return t('feat.src.site');
  var map=[['nuffic.nl','nuffic'],['technasium.nl','technasium'],['montessori.nl','montessori'],['dalton.nl','dalton'],['jenaplan.nl','jenaplan'],['vrijescholen.nl','vrije'],['dutchinternationalschools.nl','dis'],['sio.nl','sio'],['duo.nl','duo']],i;
  for(i=0;i<map.length;i++){if(host.length>=map[i][0].length&&host.slice(-map[i][0].length)===map[i][0])return t('feat.src.'+map[i][1])}
  return t('feat.src.other');
}
/* only high and medium confidence; low is never shown */
function featList(id){
  var f=DB.feat&&DB.feat.schools&&DB.feat.schools[id],out=[];
  if(!f||!Array.isArray(f.flags))return out;
  FT_ORDER.forEach(function(k){
    if(f.flags.indexOf(k)<0)return;
    var c=f.confidence&&f.confidence[k];if(c!=='high'&&c!=='medium')return;
    out.push({k:k,c:c,ev:f.evidence&&f.evidence[k]||null});
  });
  return out;
}
function hasFeat(id,sel){
  if(!sel.length)return true;
  var l=featList(id),i;
  for(i=0;i<l.length;i++){if(sel.indexOf(l[i].k)>-1)return true}
  return false;
}
function featChips(s){
  var l=featList(s.id);if(!l.length)return null;
  var box=h('div',{class:'fts'});
  l.forEach(function(x){
    var ev=x.ev,src=ev?featSrcName(ev[0],ev[2]):t('feat.src.site');
    var tip=t('feat.tip',{label:ftLbl(x.k),src:src,checked:ev&&ev[3]?t('feat.checked',{date:ev[3]}):'',less:x.c==='medium'?t('feat.less'):''});
    var url=ev&&safeUrl(ev[0]);
    box.appendChild(url?h('a',{class:'ft'+(x.c==='medium'?' md':''),href:url,target:'_blank',rel:'noopener',title:tip,text:ftLbl(x.k)}):h('span',{class:'ft'+(x.c==='medium'?' md':''),title:tip,text:ftLbl(x.k)}));
  });
  return box;
}
function safeUrl(u){return typeof u==='string'&&/^https?:\/\/[^\s"'<>]+$/i.test(u)?u:null}
function todayStart(){var d=new Date();return new Date(d.getFullYear(),d.getMonth(),d.getDate())}
function odDate(iso){var m=/^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);return m?new Date(+m[1],+m[2]-1,+m[3]):null}
/* next open day on or after today in the viewer's time zone; past dates are never returned */
function nextOpen(id){
  var f=DB.feat&&DB.feat.schools&&DB.feat.schools[id];if(!f||!Array.isArray(f.open_days))return null;
  var td=todayStart(),best=null,bd=null;
  f.open_days.forEach(function(o){
    var d=odDate(o.date);if(!d||d<td)return;
    if(!bd||d<bd){best=o;bd=d}
  });
  return best?{o:best,d:bd}:null;
}
function odNote(o){
  var n=[];
  if(o.inferred)n.push(t('od.inferred'));
  if(o.shared_site)n.push(t('od.shared'));
  return n;
}
function openLine(s){
  var n=nextOpen(s.id);if(!n)return null;
  var o=n.o,url=safeUrl(o.url);
  var box=h('div',{class:'od'});
  box.appendChild(h('span',null,[h('b',{text:t('od.next',{label:odLabel(o.label,true)})+' '}),fmtDate(n.d)]));
  if(url){box.appendChild(document.createTextNode(' · '));box.appendChild(h('a',{href:url,target:'_blank',rel:'noopener',text:t('od.source')}))}
  var notes=odNote(o);notes.push(t('od.check'));
  box.appendChild(h('small',{text:notes.join(' · ')}));
  return box;
}
/* soonest upcoming open days among the secondary schools near the postcode (same levels and distance as the list), max 3 */
function nearbyOpenDays(){
  var pt=DB.status==='ready'&&DB.feat?pcPoint():null;if(!pt)return null;
  var chips=activeChips();
  var found=nearest(DB.vo,pt,function(s){return chipMatch(s,chips)},state.radius),list=[];
  found.forEach(function(r){var n=nextOpen(r.s.id);if(n)list.push({s:r.s,d:r.d,n:n})});
  if(!list.length)return null;
  list.sort(function(a,b){return a.n.d-b.n.d||a.d-b.d});
  var box=h('div',{class:'do'},[h('b',{text:t('od.nearTitle')})]);
  var ul=h('ul',{class:'ods'});
  list.slice(0,3).forEach(function(x){
    var o=x.n.o,url=safeUrl(o.url),notes=odNote(x.n.o);
    var li=h('li',null,[h('b',{text:fmtDate(x.n.d)+': '}),url?h('a',{href:url,target:'_blank',rel:'noopener',text:x.s.name}):x.s.name,' '+t('od.nearMeta',{label:odLabel(o.label,true),km:kmStr(x.d)})]);
    if(notes.length)li.appendChild(h('small',{text:notes.join(' · ')}));
    ul.appendChild(li);
  });
  box.appendChild(ul);
  box.appendChild(h('p',{class:'note',style:'color:inherit',text:t('od.nearNote')}));
  return box;
}
function featFilter(opts,sel,onchange,idp){
  var label=t('ff.showOnly');
  var g=h('div',{class:'ctrl',role:'group','aria-label':label.replace(/[:\s]+$/,'')});
  g.appendChild(h('span',{class:'ffl',style:'align-self:center;margin:0 4px 0 0',text:label}));
  opts.forEach(function(k){
    g.appendChild(h('button',{class:'chip',type:'button',id:'ff-'+idp+'-'+k,'aria-pressed':sel.indexOf(k)>-1?'true':'false',text:ftShort(k),onclick:function(){
      var i=sel.indexOf(k);if(i>-1)sel.splice(i,1);else sel.push(k);onchange()}}));
  });
  return g;
}

/* ================= geometry ================= */
function km(lat1r,cos1,lon1,lat2r,cos2,lon2){
  var dl=(lat2r-lat1r)/2,dn=(lon2-lon1)*Math.PI/360;
  var a=Math.sin(dl)*Math.sin(dl)+cos1*cos2*Math.sin(dn)*Math.sin(dn);
  return 12742*Math.asin(Math.min(1,Math.sqrt(a)));
}
function nearest(list,pt,test,maxKm){
  var res=[],i,s,d,lr=pt[0]*Math.PI/180,cl=Math.cos(lr);
  for(i=0;i<list.length;i++){s=list[i];if(s.g===3||s.lat==null)continue;if(test&&!test(s))continue;
    d=km(lr,cl,pt[1],s.latR,s.cosL,s.lon);if(maxKm&&d>maxKm)continue;res.push({s:s,d:d})}
  res.sort(function(a,b){return a.d-b.d});
  return res;
}
function fmtKm(d){return d<1?t('unit.lessThanOne'):d<10?dec1(d):numF(Math.round(d))}
function kmStr(d){return t('unit.km',{n:fmtKm(d)})}

/* ================= model: where is the child now ================= */
function yl(y){return y+'-'+String((y+1)%100).padStart(2,'0')}
function schoolYearNow(){var d=new Date();return d.getMonth()>=7?d.getFullYear():d.getFullYear()-1}
var STOP_START={pre:4,g12:4,g35:6,g67:9,g8:11,vo1:12,vo23:13,fin:15,he:18};
var ORDER=['pre','g12','g35','g67','g8','vo1','vo23','fin','he'];
function model(){
  var a=state.age==='u4'?3:+state.age,cur,ae,g;
  if(a<4){cur='pre';ae=a}
  else if(a<=5){cur='g12';ae=a}
  else if(a<=8){cur='g35';ae=a}
  else if(a===9){cur='g67';ae=9}
  else if(a<=12){
    g=state.grp||(a===10?'7':a===11?'8':'vo');
    if(g==='6'){cur='g67';ae=9}else if(g==='7'){cur='g67';ae=10}else if(g==='8'){cur='g8';ae=11}else{cur='vo1';ae=12}
  }
  else if(a<=14){cur='vo23';ae=a}
  else if(a<=17){cur='fin';ae=a}
  else{cur='he';ae=18}
  return {age:a,cur:cur,ae:ae,sy:schoolYearNow()};
}

/* advice options as the government lists them; labels are lvl.<key> */
var ADV=['pro','bb','bbkb','kb','kbgt','gt','gthavo','havo','havovwo','vwo'];
var TYPE=['pro','bb','kb','gt','havo','vwo'];
var CHIP_DEF=[['pro',1],['bb',2],['kb',4],['gt',24],['havo',32],['vwo',64],['gym',128],['ib',512]];
var LEVEL_CHIPS={pro:['pro'],bb:['bb'],bbkb:['bb','kb'],kb:['kb'],kbgt:['kb','gt'],gt:['gt'],gthavo:['gt','havo'],havo:['havo'],havovwo:['havo','vwo'],vwo:['vwo']};
var LEVEL_GROUPS={pro:['pro'],bb:['vbk'],bbkb:['vbk'],kb:['vbk'],kbgt:['vbk','vgt'],gt:['vgt'],gthavo:['vgt','havo'],havo:['havo'],havovwo:['havo','vwo'],vwo:['vwo']};
function activeChips(){
  if(state.chips)return state.chips;
  return LEVEL_CHIPS[state.level]||[];
}
function groupsNow(){return LEVEL_GROUPS[state.level]||['pro','vbk','vgt','havo','vwo']}

/* ================= school rows ================= */
function scholenLink(s,sector){
  var q=encodeURIComponent((s.name+' '+(s.city||'')).replace(/\s+/g,' ').trim());
  return 'https://scholenopdekaart.nl/zoeken/'+(sector==='po'?'basisscholen':'middelbare-scholen')+'?zoektermen='+q+'&weergave=Lijst';
}
function safeWeb(w){return w&&/^[a-z0-9][a-z0-9.\-\/_%?=&:~#+@]*$/i.test(w)?'https://'+w:null}
function links(s,sector){
  var box=h('div',{class:'lk'});
  box.appendChild(h('a',{href:scholenLink(s,sector),target:'_blank',rel:'noopener',text:t('link.sodk')}));
  var w=safeWeb(s.web);if(w)box.appendChild(h('a',{href:w,target:'_blank',rel:'noopener',text:t('link.site')}));
  return box;
}
function pupilsText(s){
  if(s.pupils==null)return null;
  return t(s.pupils_lb?'pupils.atLeast':'pupils.about',{n:s.pupils});
}
var SEG=[['pro',[0,1]],['vbk',[2,3,4]],['vgt',[5,6]],['havo',[7,8]],['vwo',[9,10]]];
function adviceBlock(s){return adviceBar(s.adv)}
function adviceBar(a){
  var box=h('div',{class:'adv'});
  if(!a||!a[2]||a[0]<15||a[1]>6){
    box.appendChild(h('p',{class:'advn',text:a&&a[0]>0?t('adv.hidden',{n:a[0],hidden:a[1]}):t('adv.none')}));
    return box;
  }
  var sh=a[2],parts=[],bar=h('div',{class:'bar',role:'img'});
  SEG.forEach(function(g){
    var v=0;g[1].forEach(function(i){v+=sh[i]||0});
    if(v>0){bar.appendChild(h('i',{class:'a-'+g[0],style:'width:'+v+'%'}));parts.push({v:v,txt:t('adv.part',{label:t('seg.'+g[0]),pct:Math.round(v)})})}
  });
  parts.sort(function(x,y){return y.v-x.v});
  var sum=parts.map(function(p){return p.txt}).join(t('sep.list'));
  bar.setAttribute('aria-label',t('adv.aria',{list:sum}));
  box.appendChild(bar);
  box.appendChild(h('div',{class:'advn',text:t('adv.line',{list:sum,n:a[0]})+(a[1]>0?t('adv.partial'):'')}));
  return box;
}
function primaryRow(r){
  var s=r.s,main=h('div');
  main.appendChild(h('a',{class:'nm',href:U.school(s.id),text:s.name}));
  main.appendChild(h('div',{class:'mt',text:[s.city,s.denT,pupilsText(s)].filter(Boolean).join(' · ')}));
  var fc=featChips(s);if(fc)main.appendChild(fc);
  if(!s.sbo)main.appendChild(adviceBlock(s));
  var ol=openLine(s);if(ol)main.appendChild(ol);
  main.appendChild(links(s,'po'));
  main.appendChild(h('div',{class:'rowact'},cmpBtn(s)));
  return h('li',{class:'sch',style:'list-style:none'},[distCell(r,s),main]);
}
function distCell(r,s){return h('div',{class:'km'},[kmStr(r.d),h('small',{text:t(s.g>0?'row.approx':'row.about')})])}
function badge(k){return has('badge.'+k)?t('badge.'+k):k}
function trackBadges(s){
  var tr=s.tracks,wrap=h('div'),groups=0;
  var defs=[['pro',1],['bb',2],['kb',4],['gl',8],['tl',16],['havo',32],['vwo',64],['gym',128],['ib',512],['ess',1024]];
  defs.forEach(function(d){if(tr&d[1]){wrap.appendChild(h('span',{class:'tr t-'+d[0],text:badge(d[0])}))}});
  if(tr&30)groups++;if(tr&32)groups++;if(tr&64)groups++;
  if(groups>=2)wrap.appendChild(h('span',{class:'broad',text:t('broad',{n:groups})}));
  return wrap;
}
function examLine(s){
  if(!s.exam||!s.exam.length)return h('div',{class:'exam'},[h('span',{class:'small',text:t('exam.none')})]);
  var box=h('div',{class:'exam'});
  s.exam.forEach(function(e){
    var rest;
    if(e[1]==null)rest=t('exam.hidden');
    else if(e[1]<30)rest=t('exam.few',{n:e[1]})+(e[3]?t('exam.partial'):'');
    else rest=t('exam.pass',{pct:Math.round(e[2]),n:e[1]})+(e[3]?t('exam.partial'):'');
    box.appendChild(h('span',{class:e[1]!=null&&e[1]>=30?'':'small'},[h('span',{class:'tr t-'+e[0],text:badge(e[0]),style:'margin-inline-end:4px'}),rest]));
  });
  return box;
}
function secondaryRow(r,noExam){
  var s=r.s,main=h('div');
  main.appendChild(h('a',{class:'nm',href:U.school(s.id),text:s.name}));
  main.appendChild(h('div',{class:'mt',text:[s.city,s.denT,pupilsText(s)].filter(Boolean).join(' · ')}));
  main.appendChild(h('div',{style:'margin-top:5px'},trackBadges(s)));
  var fc=featChips(s);if(fc)main.appendChild(fc);
  if(!noExam)main.appendChild(examLine(s));
  var ol=openLine(s);if(ol)main.appendChild(ol);
  main.appendChild(links(s,'vo'));
  main.appendChild(h('div',{class:'rowact'},cmpBtn(s)));
  return h('li',{class:'sch',style:'list-style:none'},[distCell(r,s),main]);
}

/* ================= panels ================= */
function loadingBox(){
  return h('div',{role:'status'},[h('div',{class:'load','aria-hidden':'true'},[h('i'),h('i'),h('i'),h('i'),h('i')]),h('p',{class:'note',text:t('load.data')})]);
}
function errorBox(){
  return h('div',{class:'errbox'},[h('p',{style:'margin:0 0 6px;font-weight:700',text:t('err.data')}),
    h('button',{class:'btn sec',type:'button',id:'retry',text:t('btn.retry'),onclick:function(){loadData()}})]);
}
function dataYear(key){
  var m=DB.meta&&DB.meta.data_years&&DB.meta.data_years[key];if(!m)return {range:'',date:''};
  var a=/^(\d{4}-\d{4})/.exec(m),d=/(\d{4}-\d{2}-\d{2})/.exec(m);
  return {range:a?a[1]:'',date:d?d[1]:''};
}
function noPc(){return h('div',{class:'empty',text:t('panel.noPc')})}
function pcPoint(){return DB.pc4&&DB.pc4[state.pc]?DB.pc4[state.pc]:null}

function panelPrimary(openByDefault){
  var det=h('details',{class:'sp',open:openByDefault?true:null,id:'sp-po'});
  det.appendChild(h('summary',null,[h('h4',{text:t('panel.po.title',{pc:state.pc})}),h('div',{class:'sub',text:t('panel.po.sub')})]));
  var body=h('div');det.appendChild(body);
  if(DB.status==='loading'){body.appendChild(loadingBox());return det}
  if(DB.status==='error'){body.appendChild(errorBox());return det}
  var pt=pcPoint();if(!pt){body.appendChild(noPc());return det}
  var all=nearest(DB.po,pt,function(s){return !s.sbo&&hasFeat(s.id,ffPo)}),sbo=nearest(DB.po,pt,function(s){return s.sbo});
  var pu=dataYear('po_pupils'),ad=dataYear('po_advice');
  body.appendChild(h('p',{class:'note',style:'margin-top:0',text:t('panel.po.note',{date:pu.date,range:ad.range})}));
  if(DB.feat){
    body.appendChild(featFilter(FT_FILTER_PO,ffPo,function(){nPo=15;render()},'po'));
    if(ffPo.length)body.appendChild(h('p',{class:'ffl',text:t('panel.po.ffCount',{n:all.length})}));
  }
  var ul=h('ul',{style:'padding:0;margin:0'});
  if(!all.length)body.appendChild(h('div',{class:'empty',text:t('panel.po.empty')}));
  all.slice(0,nPo).forEach(function(r){ul.appendChild(primaryRow(r))});
  body.appendChild(ul);
  if(all.length>nPo)body.appendChild(h('button',{class:'btn sec more',type:'button',id:'more-po',text:t('btn.more',{n:15,left:all.length-nPo}),onclick:function(){nPo+=15;render()}}));
  if(sbo.length){
    var d2=h('details',{id:'sbo',style:'margin-top:12px',open:poSboOpen?true:null,ontoggle:function(e){poSboOpen=e.target.open}},[
      h('summary',{style:'cursor:pointer;font-weight:700',text:t('panel.sbo.title')}),
      h('p',{class:'note',text:t('panel.sbo.note')})]);
    var u2=h('ul',{style:'padding:0;margin:0'});
    sbo.slice(0,5).forEach(function(r){u2.appendChild(primaryRow(r))});
    d2.appendChild(u2);body.appendChild(d2);
  }
  return det;
}

function chipMatch(s,chips){
  if(!chips.length)return s.tracks>0;
  var m=0;CHIP_DEF.forEach(function(c){if(chips.indexOf(c[0])>-1)m|=c[1]});
  return (s.tracks&m)!==0;
}
function panelSecondary(){
  var sec=h('section',{class:'sp',id:'sp-vo'});
  sec.appendChild(h('h4',{text:t('panel.vo.title',{pc:state.pc})}));
  sec.appendChild(h('div',{class:'sub',text:t('panel.vo.sub')}));
  if(DB.status==='loading'){sec.appendChild(loadingBox());return sec}
  if(DB.status==='error'){sec.appendChild(errorBox());return sec}
  var pt=pcPoint();if(!pt){sec.appendChild(noPc());return sec}
  var chips=activeChips();
  var group=h('div',{class:'ctrl',role:'group','aria-label':t('panel.vo.levels')});
  CHIP_DEF.forEach(function(c){
    group.appendChild(h('button',{class:'chip',type:'button',id:'chip-'+c[0],'aria-pressed':chips.indexOf(c[0])>-1?'true':'false',text:t('chips.'+c[0]),onclick:function(){
      var cur=activeChips().slice(),i=cur.indexOf(c[0]);if(i>-1)cur.splice(i,1);else cur.push(c[0]);
      state.chips=cur;nVo=15;save();render()}}));
  });
  sec.appendChild(group);
  if(state.chips&&state.level&&LEVEL_CHIPS[state.level]){
    sec.appendChild(h('button',{class:'chip',type:'button',id:'chip-reset',text:t('panel.vo.reset'),onclick:function(){state.chips=null;save();render()}}));
  }
  var rad=h('div',{class:'rad'},[h('label',{for:'sel-radius',text:t('panel.vo.within')}),
    h('select',{id:'sel-radius',onchange:function(e){state.radius=+e.target.value;nVo=15;save();render()}},
      [5,10,20,30].map(function(v){return h('option',{value:String(v),selected:state.radius===v?true:null,text:t('unit.km',{n:v})})}))]);
  sec.appendChild(rad);
  if(DB.feat){
    sec.appendChild(featFilter(FT_FILTER_VO,ffVo,function(){nVo=15;render()},'vo'));
  }
  var found=nearest(DB.vo,pt,function(s){return chipMatch(s,chips)&&hasFeat(s.id,ffVo)},state.radius);
  var ex=dataYear('vo_exams'),pu=dataYear('vo_pupils');
  sec.appendChild(h('p',{class:'note',style:'margin-top:0',text:t(chips.length?'panel.vo.sumLevels':'panel.vo.sumAll')+(ffVo.length?t('panel.vo.sumFeat'):'')+t('panel.vo.count',{n:found.length,km:state.radius})+(found.length>nVo?t('panel.vo.showing',{n:nVo}):'.')}));
  if(!found.length){sec.appendChild(h('div',{class:'empty',text:t('panel.vo.empty',{km:state.radius})}))}
  var ul=h('ul',{style:'padding:0;margin:0'});
  found.slice(0,nVo).forEach(function(r){ul.appendChild(secondaryRow(r))});
  sec.appendChild(ul);
  if(found.length>nVo)sec.appendChild(h('button',{class:'btn sec more',type:'button',id:'more-vo',text:t('btn.more',{n:15,left:found.length-nVo}),onclick:function(){nVo+=15;render()}}));
  sec.appendChild(h('p',{class:'note',text:t('panel.vo.note',{range:ex.range,date:pu.date})}));
  return sec;
}
function panelIsk(){
  var sec=h('section',{class:'sp',id:'sp-isk'});
  sec.appendChild(h('h4',{text:t('panel.isk.title',{pc:state.pc})}));
  sec.appendChild(h('div',{class:'sub',text:t('panel.isk.sub')}));
  if(DB.status==='loading'){sec.appendChild(loadingBox());return sec}
  if(DB.status==='error'){sec.appendChild(errorBox());return sec}
  var pt=pcPoint();if(!pt){sec.appendChild(noPc());return sec}
  var rr=Math.max(state.radius,20);
  var found=nearest(DB.vo,pt,function(s){return s.isk},rr);
  if(!found.length)sec.appendChild(h('div',{class:'empty',text:t('panel.isk.empty',{km:rr})}));
  var ul=h('ul',{style:'padding:0;margin:0'});
  found.slice(0,nIsk).forEach(function(r){ul.appendChild(secondaryRow(r,true))});
  sec.appendChild(ul);
  if(found.length>nIsk)sec.appendChild(h('button',{class:'btn sec more',type:'button',id:'more-isk',text:t('btn.showMore'),onclick:function(){nIsk+=10;render()}}));
  sec.appendChild(h('p',{class:'note',text:t('panel.isk.note')}));
  return sec;
}

/* ================= inline questions ================= */
function selectQ(id,label,opts,value,onchange,hint){
  var wrap=h('div',{class:'q-inline'});
  wrap.appendChild(h('label',{for:id,text:label}));
  var sel=h('select',{class:'fld',id:id,onchange:onchange});
  opts.forEach(function(o){sel.appendChild(h('option',{value:o[0],selected:o[0]===value?true:null,text:o[1]}))});
  wrap.appendChild(sel);
  wrap.appendChild(h('span',{class:'opt',text:hint||t('q.optional')}));
  return wrap;
}
function qGroup(m){
  var a=m.age;if(a<10||a>12)return null;
  var cur=state.grp||(a===10?'7':a===11?'8':'vo');
  return selectQ('q-grp',t('q.grp.label'),[['6',t('q.grp.6')],['7',t('q.grp.7')],['8',t('q.grp.8')],['vo',t('q.grp.vo')]],cur,function(e){state.grp=e.target.value;nVo=15;save();render()},t('q.grp.hint'));
}
function qLevel(m){
  var a=m.age;if(a<10||a>15)return null;
  var inVo=(m.cur==='vo1'||m.cur==='vo23'||m.cur==='fin');
  var opts=[['',t(inVo?'q.level.notSure':'q.level.notYet')]].concat((inVo?TYPE:ADV).map(function(k){return [k,t('lvl.'+k)]}));
  var val=state.level;
  if(!opts.some(function(o){return o[0]===val}))val='';
  return selectQ('q-level',t(inVo?'q.level.labelIn':'q.level.label'),opts,val,function(e){state.level=e.target.value;state.chips=null;nVo=15;save();render()});
}
function qNew(m){
  if(m.age<4)return null;
  var w=h('div',{class:'q-inline chk'});
  w.appendChild(h('label',{for:'q-newc'},[h('input',{type:'checkbox',id:'q-newc',checked:state.newc?true:null,onchange:function(e){state.newc=e.target.checked;nIsk=10;save();render()}}),
    h('span',null,[t('q.new.label')])]));
  w.appendChild(h('span',{class:'opt',text:t('q.new.hint')}));
  return w;
}

/* ================= stop content ================= */
var ADV_ISO=['2027-01-31','2027-02-12','2027-03-24','2027-03-31'];
function advDate(i){var a=tv('adv.dates');return (a&&a[i])||{lab:'',t:'',d:''}}
function nextDated(){
  var now=new Date(),i;
  for(i=0;i<ADV_ISO.length;i++){if(new Date(ADV_ISO[i]+'T23:59:59')>=now)return i}
  return -1;
}
/* when line: school year only. The typical age has its own block (ageBox) */
function whenText(id,m){
  if(id===m.cur)return t('when.now',{sy:yl(m.sy)});
  if(id==='he'||id==='pre')return '';
  return t('when.year',{sy:yl(m.sy+(STOP_START[id]-m.ae))});
}
function advYearLabel(m){
  var y=m.sy+(11-m.ae);
  return t('adv.yearLabel',{y:String(y+1),sy:yl(y)});
}
function ageBox(id){
  var key='stops.'+id+'.age';
  if(!has(key))return null;
  var unit=has('stops.'+id+'.unit')?t('stops.'+id+'.unit'):'';
  var box=h('div',{class:'agebox'},[
    h('span',{class:'agek',text:t('age.typical')}),' ',h('b',{class:'agev',text:t(key)}),
    unit?h('span',{class:'agegrp',text:unit}):null]);
  return h('div',{class:'agewrap'},[box,h('p',{class:'agenote',text:t('age.note')})]);
}

function buildStops(m){
  var idx=ORDER.indexOf(m.cur),list=[],grp=groupsNow();
  ORDER.slice(idx).forEach(function(id){list.push(stopDef(id,m,grp))});
  if(state.newc&&m.age>=4){
    var young=m.age<12&&(m.cur!=='vo1'&&m.cur!=='vo23'&&m.cur!=='fin'&&m.cur!=='he');
    var k=young?'stops.newc.young':'stops.newc.old';
    var nst={id:'newc',icon:'globe',side:true,
      title:t(k+'.title'),
      when:t('stops.newc.when'),
      what:[t(k+'.what')],
      todo:tv('stops.newc.todo'),
      src:['nieuw','loket'],schools:m.age>=10?'isk':null};
    list.splice(1,0,nst);
  }
  return list;
}

function pathText(grp){
  var out=[];
  ['pro','vbk','vgt','havo','vwo'].forEach(function(g){if(grp.indexOf(g)>-1)out.push(t('path.'+g))});
  return out;
}

var STOP_ICON={pre:'clock',g12:'school',g35:'school',g67:'book',g8:'fork',vo1:'school',vo23:'pencil',fin:'pencil',he:'cap'};
var STOP_SRC={pre:['basis','wanneer','rijksoverheid_when_to_register_at_a_prim','oco_amsterdam_when_to_register','oco_amsterdam_priority_rules_for_primary'],g12:['wanneer','blijven'],g35:['blijven','loket'],g67:['tijdlijn','loket'],g8:['tijdlijn','voraad','advies','inschr','weiger'],vo1:['brug','weiger','loket'],vo23:['vmbo','havo','vwo','vo_raad_moving_from_vmbo_to_havo_and_fro','mboRijks'],fin:['mboToel','mboRijks','kiesmbo','vmbo','havo','vwo','vo_raad_moving_from_vmbo_to_havo_and_fro','pro','advies'],he:['schema','gov','sk123','sk21','rijksoverheid_which_diplomas_give_access','mboRijks','nuf']};
function stopDef(id,m,grp){
  var s={id:id,icon:STOP_ICON[id],when:whenText(id,m),title:t('stops.'+id+'.title'),schools:null,src:STOP_SRC[id].slice(),todo:tv('stops.'+id+'.todo')||[],what:(tv('stops.'+id+'.what')||[]).slice()};
  var cur=(m.cur===id);
  switch(id){
  case 'pre':s.schools='po';break;
  case 'g12':case 'g35':case 'g67':s.schools=cur?'po':null;break;
  case 'g8':
    s.deadline=true;
    if(m.sy+(11-m.ae)===2026){
      s.dated={nx:nextDated()};
      s.what.push(t('stops.g8.whatDated'));
    }else{
      s.what.push(t('stops.g8.whatUsual',{label:advYearLabel(m)}));
    }
    s.schools='vo';
    if(cur||m.age>=10)s.schools2='po';
    break;
  case 'vo1':s.schools=(cur&&m.age<=15)?'vo':null;break;
  case 'vo23':s.schools=cur?'vo':null;break;
  case 'fin':s.deadline=true;s.what=s.what.concat(pathText(grp));s.schools=(cur&&m.age<=15)?'vo':null;break;
  }
  return s;
}

/* ================= next action card ================= */
function nextCard(m){
  var box=h('section',{class:'nextcard','aria-label':t('next.aria')});
  var lab=t('next.label'),date='',title='',text='',more=null;
  var nx=nextDated();
  var onG8=(m.cur==='g8'&&m.sy+(11-m.ae)===2026);
  if(onG8&&nx>=0){
    var d=advDate(nx);date=d.lab;title=d.t;text=d.d;
    more=t('next.g8.more');
  }else if(m.cur==='pre'){
    date=t('next.pre.date');title=t('next.pre.title');text=t('next.pre.text');
  }else if(m.cur==='g8'||m.cur==='g67'){
    lab=t('next.coming');date=advYearLabel(m);title=t('next.adv.title');
    text=t(m.cur==='g8'?'next.g8.text':'next.g67.text');
  }else if(m.cur==='g12'||m.cur==='g35'){
    lab=t('next.nothing');date=advYearLabel(m);title=t('next.early.title');text=t('next.early.text');
  }else if(m.cur==='vo1'||m.cur==='vo23'){
    date=t('next.vo.date');title=t('next.vo.title');text=t('next.vo.text');
  }else if(m.cur==='fin'){
    date=t('next.fin.date');title=t('next.fin.title');text=t('next.fin.text');
  }else{
    date=t('next.he.date');title=t('next.he.title');text=t('next.he.text');
  }
  box.appendChild(h('div',{class:'nl',text:lab}));
  box.appendChild(h('div',{class:'nd',text:date}));
  var nb=h('div',{class:'nb'},[h('h3',{text:title}),h('p',{text:text})]);
  if(more)nb.appendChild(h('p',{style:'font-size:.85rem',text:more}));
  box.appendChild(nb);
  return box;
}

/* ================= route rendering ================= */
function renderStop(st,m,idx,firstDeadlineId){
  var isNow=(idx===0);
  var isNext=(st.id===firstDeadlineId);
  var cls='stop'+(isNow?' now':'')+(isNext?' next':'')+(st.side?' side':'');
  var li=h('li',{class:cls});
  li.appendChild(h('span',{class:'tick','aria-hidden':'true'}));
  var tags=h('div',{class:'tags'});
  if(isNow)tags.appendChild(h('span',{class:'tg y',text:t('tag.here')}));
  if(isNext)tags.appendChild(h('span',{class:'tg y',text:t(isNow?'tag.nextAction':'tag.nextDeadline')}));
  if(st.side)tags.appendChild(h('span',{class:'tg',text:t('tag.side')}));
  if(tags.firstChild)li.appendChild(tags);
  var hd=h('div',{class:'shd'},[st.when?h('div',{class:'when',text:st.when}):null,h('h3',{text:st.title})]);
  var head=h('div',{class:'shead'},[h('span',{class:'pic'},ico(st.icon)),hd]);
  li.appendChild(head);
  var ab=st.side?h('div',{class:'agewrap'},[h('div',{class:'agebox'},[h('span',{class:'agek',text:t('age.typical')}),' ',h('b',{class:'agev',text:t('stops.newc.age')}),h('span',{class:'agegrp',text:t('stops.newc.unit')})]),h('p',{class:'agenote',text:t('age.note')})]):ageBox(st.id);
  if(ab)li.appendChild(ab);
  var info=h('div',{class:'sinfo'});
  st.what.forEach(function(w){info.appendChild(hr('p','',w))});
  if(st.dated){
    var ul=h('ol',{class:'dated',style:'padding:0'});
    ADV_ISO.forEach(function(iso,i){
      var d=advDate(i);
      var cl=i<st.dated.nx||st.dated.nx<0?'past':(i===st.dated.nx?'nx':'');
      ul.appendChild(h('li',{class:cl},[h('span',{class:'dd',text:d.lab}),h('span',{class:'dt',text:d.t}),h('span',{class:'dx',text:d.d})]));
    });
    info.appendChild(ul);
    if(has('stops.'+st.id+'.afterSignup'))info.appendChild(hr('p','',t('stops.'+st.id+'.afterSignup')));
  }
  if(has('stops.'+st.id+'.note.text')){
    info.appendChild(h('div',{class:'callout',role:'note'},[h('b',{text:t('stops.'+st.id+'.note.title')}),hr('p','',t('stops.'+st.id+'.note.text'))]));
  }
  if(st.todo.length){
    var d2=h('div',{class:'do'},[h('b',{text:t('stop.todo')})]);
    var u=h('ul');st.todo.forEach(function(x){u.appendChild(h('li',{text:x}))});d2.appendChild(u);info.appendChild(d2);
  }
  if((st.id==='g8'||st.id==='g67')&&(m.age>=10||state.level||preview)){
    var od=nearbyOpenDays();if(od)info.appendChild(od);
  }
  if(st.id==='g8'&&DB.pc4&&DB.pc4[state.pc]&&DB.pc4[state.pc][2]==='Amsterdam'){
    info.appendChild(h('div',{class:'do'},[h('b',{text:t('amsterdam.title')}),h('p',{style:'margin-top:4px',text:t('amsterdam.text')})]));
  }
  if(isNow){
    [qGroup(m),qLevel(m),qNew(m)].forEach(function(q){if(q)info.appendChild(q)});
  }
  if(st.src.length)info.appendChild(srcLine(st.src));
  var panels=[];
  if(st.schools==='po')panels.push(panelPrimary(true));
  if(st.schools==='vo'){
    if(m.age>=10||state.level||preview)panels.push(panelSecondary());
    else panels.push(previewBox());
  }
  if(st.schools==='isk')panels.push(panelIsk());
  if(st.schools2==='po'&&m.age<12&&m.cur==='g8')panels.push(panelPrimary(false));
  var body=h('div',{class:'sbody'+(panels.length?' two':'')},[info]);
  if(panels.length){var col=h('div',{style:'min-width:0'});panels.forEach(function(p){col.appendChild(p)});body.appendChild(col)}
  li.appendChild(body);
  return li;
}
function previewBox(){
  var b=h('div',{class:'sp'});
  b.appendChild(h('h4',{text:t('panel.vo.title',{pc:state.pc})}));
  b.appendChild(h('p',{class:'sub',text:t('preview.sub')}));
  b.appendChild(h('button',{class:'btn sec',type:'button',id:'btn-preview',text:t('preview.btn'),onclick:function(){preview=true;render()}}));
  return b;
}

function render(){if(VIEW==='route')renderRoute()}
function ageText(){
  return state.age==='u4'?t('route.age.u4'):state.age==='18'?t('route.age.18'):t('route.age.n',{age:state.age});
}
function renderRoute(){
  var active=document.activeElement&&document.activeElement.id;
  var rb=$('resbar'),mu=$('muni');clear(rb);clear(mu);
  var empty=!hasInput();
  $('route-empty').hidden=!empty;
  $('route-body').hidden=empty;
  if(empty){
    $('resmeta').textContent='';
    return;
  }
  var m=model();
  var stops=buildStops(m);
  var pt=DB.pc4&&DB.pc4[state.pc];
  if(state.example)rb.appendChild(h('span',{class:'extag',text:t('route.exampleTag')}));
  rb.appendChild(h('h2',{text:t('route.title')}));
  var place=pt?t('route.place',{place:pt[2]}):'';
  $('resmeta').textContent=state.example
    ?t('route.metaExample',{age:ageText(),pc:state.pc,place:place})
    :t('route.meta',{age:ageText(),pc:state.pc,place:place});
  if(pt){
    mu.appendChild(h('div',{class:'muni'},h('p',null,[h('b',{text:t('route.muni.in',{place:pt[2]})+' '}),t('route.muni.text')])));
  }else if(DB.status==='ready'){
    mu.appendChild(h('div',{class:'muni'},[h('p',{text:t('route.muni.unknown',{pc:state.pc})})]));
  }
  var nc=$('next');clear(nc);nc.appendChild(nextCard(m));
  var fd=null;
  for(var i=0;i<stops.length;i++){if(stops[i].deadline){fd=stops[i].id;break}}
  var r=$('route');clear(r);
  stops.forEach(function(st,i){r.appendChild(renderStop(st,m,i,fd))});
  if(active){var el=$(active);if(el&&el.focus){try{el.focus({preventScroll:true})}catch(e){}}}
}
function renderStatus(){
  var s=$('status');clear(s);
  if(DB.status==='loading')s.appendChild(loadingBox());
}
function renderGlossary(){
  var dl=$('gloss-dl');clear(dl);
  (tv('glossary')||[]).forEach(function(g){dl.appendChild(h('dt',{text:g[0]}));dl.appendChild(h('dd',{text:g[1]}))});
}
function renderExamples(){
  var box=$('exrow');clear(box);
  box.appendChild(h('span',{class:'exlbl',text:t('form.tryExample')}));
  EXAMPLES.forEach(function(e){
    box.appendChild(h('button',{class:'chip exbtn',type:'button',text:t('ex.'+e[1]),onclick:function(){startExample(e[0])}}));
  });
}
var EXAMPLES=[['1077','amsterdam'],['2517','hague'],['5611','eindhoven']];
function startExample(pc){
  state.age='11';state.pc=pc;state.example=true;state.grp='';state.level='';state.chips=null;state.newc=false;
  nPo=15;nVo=15;nIsk=10;preview=false;
  $('ferr').textContent='';$('pc').removeAttribute('aria-invalid');
  if(VIEW!=='route')navigate(U.route());else render();
  var rb=$('resbar');if(rb&&rb.scrollIntoView)rb.scrollIntoView({block:'start'});
}

/* ================= data and sources view ================= */
var FEAT_ATTR=[['nuffic','https://www.nuffic.nl/onderwijssectoren/voortgezet-onderwijs/tweetalig-onderwijs/alle-tto-scholen-in-nederland','CC BY-NC 4.0'],
  ['technasium','https://www.technasium.nl/',''],['nmv','https://montessori.nl/','NMV'],['ndv','https://dalton.nl/','NDV'],['njpv','https://jenaplan.nl/','NJPV'],
  ['vrije','https://www.vrijescholen.nl/',''],['dis','https://www.dutchinternationalschools.nl/',''],['sio','https://sio.nl/','']];
function renderFooter(){
  var d=odDate(LAST_CHECKED);
  var e=$('foot-checked');if(e)e.textContent=t('foot.checked',{date:d?fmtDay(d):LAST_CHECKED});
}
function aLink(text,url){return h('a',{href:url,target:'_blank',rel:'noopener',text:text})}
function renderSources(){
  renderFooter();
  var out=$('sources-out');if(!out)return;
  clear(out);
  var d=odDate(LAST_CHECKED);
  var card=h('div',{class:'psec'},[h('h3',{text:t('sources.check.title')}),
    h('p',{text:t('sources.check.text',{date:d?fmtDay(d):LAST_CHECKED})})]);
  out.appendChild(card);
  var rd=h('div',{class:'psec'},[h('h3',{text:t('sources.read.title')})]);
  (tv('sources.read.items')||[]).forEach(function(x){rd.appendChild(h('p',{text:x}))});
  out.appendChild(rd);
  var dt=h('div',{class:'psec'},[h('h3',{text:t('sources.data.title')})]);
  var list=DB.meta&&DB.meta.attribution;
  if(list&&list.length){
    dt.appendChild(h('p',{text:t('sources.dataline',{built:DB.meta.generated||'',pupils:dataYear('po_pupils').date,advice:dataYear('po_advice').range,exams:dataYear('vo_exams').range})}));
  }
  var at=h('ul',{class:'srclist'});
  if(DB.feat){
    var li=h('li',null,[t('attr.feat.lead')+' ']);
    FEAT_ATTR.forEach(function(a,i){
      if(i)li.appendChild(document.createTextNode(', '));
      li.appendChild(aLink(t('attr.l.'+a[0]),a[1]));
      if(a[2])li.appendChild(document.createTextNode(' ('+a[2]+')'));
    });
    li.appendChild(document.createTextNode(' '+t('attr.feat.tail')));
    at.appendChild(li);
  }
  if(list&&list.length){
    list.forEach(function(a){at.appendChild(h('li',null,[a.text+' '+t('attr.licence',{licence:a.licence})+' ',aLink(t('attr.licenceLink'),a.licence_url),' · ',aLink(t('attr.sourceLink'),a.url)]))});
    dt.appendChild(at);
    if(DB.meta.disclaimer)dt.appendChild(h('p',{text:DB.meta.disclaimer}));
  }else{
    at.appendChild(h('li',{text:t('attr.fallback')}));
    dt.appendChild(at);
    dt.appendChild(h('p',{text:t('attr.fallbackDisc')}));
  }
  dt.appendChild(h('p',{text:t('sources.sodk')}));
  out.appendChild(dt);
  var sl=h('div',{class:'psec'},[h('h3',{text:t('sources.list.title')})]);
  var u=h('ul',{class:'srclist'});
  SRC_ORDER.forEach(function(k){u.appendChild(h('li',null,aLink(t('src.'+k),SRC_URL[k])))});
  sl.appendChild(u);out.appendChild(sl);
}

/* ================= whole system diagram ================= */
function buildSystem(){
  var W=360,H=700,S=svgEl('svg',{'class':'sys-svg',viewBox:'0 0 '+W+' '+H,role:'img','aria-labelledby':'sysT sysD'});
  S.appendChild(svgEl('title',{id:'sysT'},t('sys.title')));
  S.appendChild(svgEl('desc',{id:'sysD'},t('sys.desc')));
  var defs=svgEl('defs'),mkr=svgEl('marker',{id:'ah',viewBox:'0 0 10 10',refX:'9',refY:'5',markerWidth:'13',markerHeight:'13',markerUnits:'userSpaceOnUse',orient:'auto-start-reverse'});
  mkr.appendChild(svgEl('path',{'class':'ah',d:'M0 0L10 5L0 10z'}));defs.appendChild(mkr);S.appendChild(defs);
  function rect(x,y,w,hh,cls,txt,tcls){
    S.appendChild(svgEl('rect',{'class':'cell '+cls,x:x,y:y,width:w,height:hh}));
    if(txt!==undefined&&txt!=='')S.appendChild(svgEl('text',{'class':tcls||'on',x:x+w/2,y:y+hh/2+4,'text-anchor':'middle'},txt));
  }
  function text(x,y,tx,cls,anchor){var a={'class':cls||'ax',x:x,y:y};if(anchor)a['text-anchor']=anchor;S.appendChild(svgEl('text',a,tx))}
  function path(d,dash,both){
    S.appendChild(svgEl('path',{'class':'arh',d:d}));
    var a={'class':'ar'+(dash?' d':''),d:d,'marker-end':'url(#ah)'};
    if(both)a['marker-start']='url(#ah)';
    S.appendChild(svgEl('path',a));
  }
  function mk(cx,y,tx){
    S.appendChild(svgEl('rect',{'class':'mkb',x:cx-7,y:y,width:14,height:14}));
    S.appendChild(svgEl('text',{'class':'mkt',x:cx,y:y+10.5,'text-anchor':'middle'},tx));
  }
  function bar(x,y,w,n,cls,labels){for(var i=0;i<n;i++)rect(x,y+i*20,w,20,cls,labels?labels[i]:String(i+1))}
  var LX=[40,120,200,280],LW=60,C=[70,150,230,310];
  /* primary */
  text(40,14,t('sys.primary'),'ax');
  for(var g=1;g<=8;g++){
    var y=22+(g-1)*20;
    rect(40,y,308,20,'f-bo');
    S.appendChild(svgEl('text',{'class':'on',x:48,y:y+14.5},t('sys.yearGroup',{n:String(g)})));
    S.appendChild(svgEl('text',{'class':'on',x:340,y:y+14.5,'text-anchor':'end'},t('sys.age',{n:String(g+3)})));
  }
  /* advice arrows */
  C.forEach(function(x){path('M'+x+' 184V230')});
  S.appendChild(svgEl('rect',{'class':'lbl',x:36,y:196,width:288,height:24}));
  mk(50,201,'1');text(64,213,t('sys.adviceLabel'),'ax');
  /* secondary lanes */
  var names=['pro','vmbo','havo','vwo'],cls=['f-pro','f-vbk','f-havo','f-vwo'],yrs=[5,4,5,6];
  text(34,246,t('sys.ageAxis'),'ax','end');
  for(var i=0;i<4;i++){
    rect(LX[i],232,LW,18,cls[i],t('sys.lane.'+names[i]),'hd');
    bar(LX[i],250,LW,yrs[i],cls[i]);
  }
  [12,14,16,18].forEach(function(a,k){text(34,250+k*40+14,String(a),'ax','end')});
  /* early switching and diploma moves between lanes (gaps are 20 wide: 100-120, 180-200, 260-280) */
  path('M181 278H199',true,true);path('M261 278H279',true,true);mk(190,284,'2');mk(270,284,'2');
  path('M181 314H199',true);mk(190,320,'3');
  path('M261 334H279');mk(270,340,'4');
  /* leaving school */
  path('M70 352V424',true);mk(70,380,'5');
  path('M150 332V424');mk(150,380,'6');
  path('M230 352V424');mk(230,396,'7');
  path('M214 352V392H166V424');mk(190,385,'7');
  path('M310 372V424');mk(310,396,'8');
  path('M296 372V404H258V424');mk(277,397,'8');
  /* after secondary: mbo, hbo, wo */
  rect(40,424,132,18,'f-mbo','mbo','hd');rect(200,424,62,18,'f-hbo','hbo','hd');rect(280,424,68,18,'f-wo','wo','hd');
  [1,2,3,4].forEach(function(l,k){var lb=[];for(var q=0;q<l;q++)lb.push(q===0?String(l):'');bar(40+k*34,442,30,l,'f-mbo',lb)});
  text(106,540,t('sys.mboLevels'),'ax','middle');
  bar(200,442,22,2,'f-hbo',['AD','']);
  bar(226,442,36,4,'f-hbo');
  path('M244 523V543',true);
  bar(226,544,36,2,'f-hbo',['M','']);
  bar(280,442,68,3,'f-wo');
  path('M314 503V525',true);
  bar(280,526,68,2,'f-wo',['M','']);
  path('M314 567V589',true);
  bar(280,590,68,4,'f-wo',['PhD','','','']);
  path('M173 470H199');mk(186,477,'a');
  path('M263 452H279',true);mk(271,458,'b');
  path('M263 512H271V536H279',true);mk(271,519,'d');
  text(36,692,t('sys.legend'),'ax');
  S.setAttribute('style','direction:ltr');
  return S;
}
var SYS_KEYS=['bo','pro','vbk','havo','vwo','mbo','hbo','wo'];
function renderSystem(){
  var f=$('sysfig');clear(f);f.appendChild(buildSystem());
  var k=$('syskeys');clear(k);
  SYS_KEYS.forEach(function(x){k.appendChild(h('li',null,[h('i',{style:'background:var(--c-'+x+')'}),t('sys.key.'+x)]))});
  var ol=$('xfers');clear(ol);
  (tv('sys.xfers')||[]).forEach(function(x){
    ol.appendChild(h('li',null,[h('b',{text:x.k}),h('span',null,[x.text])]));
  });
  ol.appendChild(h('li',null,[h('b',{text:'+'}),h('span',null,[t('sys.xfersExtra')])]));
  var sl=$('syssrc');clear(sl);sl.appendChild(document.createTextNode(t('src.label')+' '));
  ['schema','nuf','loket','gov','mboRijks','sk123','vo_raad_moving_from_vmbo_to_havo_and_fro','rijksoverheid_which_diplomas_give_access'].forEach(function(key,i){if(i)sl.appendChild(document.createTextNode(' · '));sl.appendChild(h('a',{href:SRC_URL[key],target:'_blank',rel:'noopener',text:t('src.'+key)}))});
}

/* ================= FAQ ================= */
function faqSetAll(open){qsa('#faq details').forEach(function(d){d.open=open})}
function faqFocus(slug){
  if(!slug||!/^[a-z0-9-]{1,60}$/.test(slug))return;
  var d=document.getElementById('faq-'+slug);if(!d)return;
  d.open=true;
  qsa('#faq details.hit').forEach(function(x){x.classList.remove('hit')});
  d.classList.add('hit');
  setTimeout(function(){try{d.scrollIntoView({block:'start',behavior:reducedMotion()?'auto':'smooth'})}catch(e){d.scrollIntoView()}},60);
}
function renderFaq(){
  var f=$('faq');clear(f);
  var groups=tv('faq.groups')||[];
  var tools=h('div',{class:'faqtools'});
  var nav=h('nav',{class:'faqnav','aria-label':t('faq.navAria')});
  groups.forEach(function(g){
    nav.appendChild(h('button',{class:'chip',type:'button',text:g.title,onclick:function(){
      var el=document.getElementById('faqg-'+g.id);if(el)el.scrollIntoView({block:'start',behavior:reducedMotion()?'auto':'smooth'})}}));
  });
  tools.appendChild(nav);
  tools.appendChild(h('div',{class:'faqall'},[
    h('button',{class:'btn sec',type:'button',text:t('faq.expand'),onclick:function(){faqSetAll(true)}}),' ',
    h('button',{class:'btn sec',type:'button',text:t('faq.collapse'),onclick:function(){faqSetAll(false)}})]));
  f.appendChild(tools);
  groups.forEach(function(g){
    var sec=h('section',{class:'faqgrp','aria-labelledby':'faqg-'+g.id});
    sec.appendChild(h('h3',{id:'faqg-'+g.id,text:g.title}));
    g.items.forEach(function(x){
      var d=h('details',{id:'faq-'+x.id,open:true});
      d.appendChild(h('summary',{text:x.q}));
      var a=h('div',{class:'ans'});
      x.blocks.forEach(function(b){
        if(b.p!==undefined)a.appendChild(hr('p','',b.p));
        else if(b.say!==undefined)a.appendChild(hr('p','say',b.say));
        else if(b.ul){var ul=h('ul');b.ul.forEach(function(li){ul.appendChild(hr('li','',li))});a.appendChild(ul)}
      });
      a.appendChild(srcLine(x.src));
      a.appendChild(h('p',{class:'faqlink'},h('a',{href:U.view('faq','?q='+x.id),text:t('faq.link')})));
      d.appendChild(a);sec.appendChild(d);
    });
    f.appendChild(sec);
  });
}

/* ================= v3: routing, search, map, profiles, compare ================= */
var VIEWS=['route','find','map','school','compare','system','faq','sources'];
var TABS=['route','find','map','system','faq','sources'];
var VIEW='route',CUR_ID='',FIRST=true,LANG_CHANGE=false;
function secShort(s){return t('sec.short.'+s.sec)}
function secLong(s){return t('sec.long.'+s.sec)}
var SEC_OPTS=['','po','sbo','vo'];
var R_OPTS=[0,2,5,10,20,50];
var PAGE=25;

function grpOf(s){return s.sec==='vo'?'vo':'po'}
function isId(x){return typeof x==='string'&&/^[0-9A-Za-z]{6}$/.test(x)}
function valTxt(v,lb){return v==null?t('val.fewer5'):lb?t('val.atLeast',{n:v}):numF(v)}

/* ---------- index ---------- */
var ALL=[],BYID={},DENS=[];
function norm(x){return String(x==null?'':x).toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g,'')}
function buildIndex(){
  ALL=[];BYID={};var dens={};
  DB.po.forEach(function(s){s.sec=s.sbo?'sbo':'po';ALL.push(s)});
  DB.vo.forEach(function(s){s.sec='vo';ALL.push(s)});
  ALL.forEach(function(s){
    var pc=String(s.pc||'').toLowerCase();
    s.nk=norm(s.name);
    s.w=(s.nk+' '+norm(s.city)+' '+norm(s.mun)+' '+pc+' '+pc.slice(0,4)).split(/[^a-z0-9]+/).filter(Boolean);
    BYID[s.id]=s;dens[s.denT]=1;
  });
  ALL.sort(function(a,b){return a.nk<b.nk?-1:a.nk>b.nk?1:(a.id<b.id?-1:1)});
  DENS=Object.keys(dens).sort();
  CMP=CMP.filter(function(id){return BYID[id]});
  saveCmp();
}

/* ---------- filter state shared by Find and Map ---------- */
var F={q:'',sec:'',tr:[],ft:[],den:'',pc:'',r:0};
function fReset(){F.q='';F.sec='';F.tr=[];F.ft=[];F.den='';F.pc='';F.r=0}
function fQuery(withFocus){
  var p=[];
  if(F.q)p.push('q='+encodeURIComponent(F.q));
  if(F.sec)p.push('sec='+F.sec);
  if(F.tr.length)p.push('tr='+F.tr.join(','));
  if(F.ft.length)p.push('ft='+F.ft.join(','));
  if(F.den)p.push('den='+encodeURIComponent(F.den));
  if(F.pc)p.push('pc='+F.pc);
  if(F.r)p.push('r='+F.r);
  if(withFocus&&MAPFOCUS)p.push('s='+MAPFOCUS);
  return p.length?'?'+p.join('&'):'';
}
function parseQ(str){
  var o={};if(!str)return o;
  str.split('&').forEach(function(kv){
    var i=kv.indexOf('='),k=i<0?kv:kv.slice(0,i),v=i<0?'':kv.slice(i+1);
    try{v=decodeURIComponent(v.replace(/\+/g,' '))}catch(e){}
    if(/^[a-z]{1,4}$/.test(k))o[k]=v;
  });
  return o;
}
function applyQuery(q){
  fReset();
  F.q=String(q.q||'').slice(0,80);
  F.sec=(q.sec==='po'||q.sec==='sbo'||q.sec==='vo')?q.sec:'';
  F.tr=String(q.tr||'').split(',').filter(function(x){return CHIP_DEF.some(function(c){return c[0]===x})});
  F.ft=String(q.ft||'').split(',').filter(function(x){return FT_ALL.indexOf(x)>-1});
  F.den=String(q.den||'').slice(0,80);
  F.pc=parsePc(q.pc||'');
  F.r=R_OPTS.some(function(o){return String(o)===String(q.r)})?+q.r:0;
}
function tokens(q){
  q=norm(q).trim();
  var m=/^([1-9]\d{3})\s*([a-z]{2})$/.exec(q);if(m)return [m[1]+m[2]];
  return q.split(/[^a-z0-9]+/).filter(Boolean);
}
function matchTok(s,tk){for(var i=0;i<s.w.length;i++){if(s.w[i].indexOf(tk)===0)return true}return false}
function trMask(){var m=0;CHIP_DEF.forEach(function(c){if(F.tr.indexOf(c[0])>-1)m|=c[1]});return m}
function fPoint(){return F.pc&&DB.pc4&&DB.pc4[F.pc]?DB.pc4[F.pc]:null}
function runFilter(){
  var toks=tokens(F.q),mask=trMask(),pt=fPoint(),out=[],i,s,k,ok,d=null,lr=0,cl=0;
  if(pt){lr=pt[0]*Math.PI/180;cl=Math.cos(lr)}
  for(i=0;i<ALL.length;i++){
    s=ALL[i];
    if(F.sec&&s.sec!==F.sec)continue;
    if(mask&&(s.sec!=='vo'||!(s.tracks&mask)))continue;
    if(F.den&&s.denT!==F.den)continue;
    if(F.ft.length&&!hasFeat(s.id,F.ft))continue;
    ok=true;for(k=0;k<toks.length;k++){if(!matchTok(s,toks[k])){ok=false;break}}
    if(!ok)continue;
    if(pt){
      if(s.g===3||s.lat==null)continue;
      d=km(lr,cl,pt[1],s.latR,s.cosL,s.lon);
      if(F.r&&d>F.r)continue;
    }
    out.push({s:s,d:pt?d:null});
  }
  if(pt)out.sort(function(a,b){return a.d-b.d});
  return out;
}

/* ---------- shared filter form ---------- */
var FORM=null,FP={},qTimer=0,pTimer=0;
function chipBtn(label,pressed,fn,id){return h('button',{class:'chip',type:'button',id:id||null,'aria-pressed':pressed?'true':'false',text:label,onclick:fn})}
function ensureForm(){
  if(FORM)return FORM;
  var f=h('div',{class:'fcard',role:'search','aria-label':t('filters.aria')});
  FP={};
  FP.q=h('input',{class:'fld',id:'f-q',type:'search',autocomplete:'off',spellcheck:'false',placeholder:t('filters.qPlaceholder'),
    oninput:function(){clearTimeout(qTimer);qTimer=setTimeout(function(){F.q=FP.q.value.slice(0,80);filterChanged()},120)}});
  f.appendChild(h('div',null,[h('label',{for:'f-q',text:t('filters.qLabel')}),FP.q]));
  FP.sec=h('div',{class:'ctrl',role:'group','aria-label':t('filters.typeAria')});
  SEC_OPTS.forEach(function(o){FP.sec.appendChild(chipBtn(t('sec.opt.'+(o||'all')),false,function(){F.sec=o;if(o&&o!=='vo')F.tr=[];filterChanged();syncForm()},'f-sec-'+(o||'all')))});
  f.appendChild(h('div',{class:'fgrp'},[h('span',{class:'fl',text:t('filters.type')}),FP.sec]));
  FP.tr=h('div',{class:'ctrl',role:'group','aria-label':t('filters.levelsAria')});
  CHIP_DEF.forEach(function(c){FP.tr.appendChild(chipBtn(t('chips.'+c[0]),false,function(){
    var i=F.tr.indexOf(c[0]);if(i>-1)F.tr.splice(i,1);else F.tr.push(c[0]);
    if(F.tr.length&&F.sec&&F.sec!=='vo')F.sec='vo';
    filterChanged();syncForm()},'f-tr-'+c[0]))});
  f.appendChild(h('div',{class:'fgrp'},[h('span',{class:'fl',text:t('filters.levels')}),FP.tr]));
  FP.ft=h('div',{class:'ctrl',role:'group','aria-label':t('filters.ftAria')});
  FT_ALL.forEach(function(k){FP.ft.appendChild(chipBtn(ftShort(k),false,function(){
    var i=F.ft.indexOf(k);if(i>-1)F.ft.splice(i,1);else F.ft.push(k);filterChanged();syncForm()},'f-ft-'+k))});
  FP.ftWrap=h('div',{class:'fgrp'},[h('span',{class:'fl',text:t('filters.ft')}),FP.ft,
    h('p',{class:'ffl',text:t('filters.ftNote')})]);
  f.appendChild(FP.ftWrap);
  var row=h('div',{class:'frow three'});
  FP.den=h('select',{class:'fld',id:'f-den',onchange:function(e){F.den=e.target.value;filterChanged()}});
  FP.den.appendChild(h('option',{value:'',text:t('filters.anyDen')}));
  DENS.forEach(function(d){FP.den.appendChild(h('option',{value:d,text:d}))});
  row.appendChild(h('div',null,[h('label',{for:'f-den',text:t('filters.den')}),FP.den]));
  FP.pc=h('input',{class:'fld',id:'f-pc',type:'text',inputmode:'text',maxlength:'8',autocomplete:'off','aria-describedby':'f-pchint',placeholder:t('form.pcPlaceholder'),
    oninput:function(){clearTimeout(pTimer);pTimer=setTimeout(function(){
      var v=FP.pc.value;F.pc=parsePc(v);FP.pcBad=!!v.trim()&&!F.pc;filterChanged()},120)}});
  row.appendChild(h('div',null,[h('label',{for:'f-pc',text:t('form.pcLabel')}),FP.pc,h('div',{class:'hint',id:'f-pchint',text:t('form.pcHint')})]));
  FP.r=h('select',{class:'fld',id:'f-r',onchange:function(e){F.r=+e.target.value;filterChanged()}});
  R_OPTS.forEach(function(o){FP.r.appendChild(h('option',{value:String(o),text:o?t('unit.km',{n:o}):t('filters.anyDistance')}))});
  row.appendChild(h('div',null,[h('label',{for:'f-r',text:t('filters.within')}),FP.r]));
  f.appendChild(row);
  FP.pcmsg=h('p',{class:'ffl',id:'f-pcmsg',role:'status',style:'margin:0'});
  f.appendChild(FP.pcmsg);
  var acts=h('div',{class:'ctrl'});
  FP.mine=h('button',{class:'btn sec',type:'button',text:t('filters.mine'),onclick:function(){F.pc=state.pc;FP.pcBad=false;filterChanged();syncForm()}});
  acts.appendChild(FP.mine);
  acts.appendChild(h('button',{class:'btn sec',type:'button',text:t('filters.clear'),onclick:function(){fReset();FP.pcBad=false;filterChanged();syncForm()}}));
  f.appendChild(acts);
  FORM=f;
  return f;
}
function syncForm(){
  if(!FORM)return;
  if(FP.q.value!==F.q&&document.activeElement!==FP.q)FP.q.value=F.q;
  SEC_OPTS.forEach(function(o){$('f-sec-'+(o||'all')).setAttribute('aria-pressed',F.sec===o?'true':'false')});
  CHIP_DEF.forEach(function(c){$('f-tr-'+c[0]).setAttribute('aria-pressed',F.tr.indexOf(c[0])>-1?'true':'false')});
  FT_ALL.forEach(function(k){$('f-ft-'+k).setAttribute('aria-pressed',F.ft.indexOf(k)>-1?'true':'false')});
  FP.ftWrap.hidden=!DB.feat;
  FP.den.value=F.den;
  if(parsePc(FP.pc.value)!==F.pc&&document.activeElement!==FP.pc)FP.pc.value=F.pc;
  FP.r.value=String(F.r);
  FP.mine.hidden=state.example||!hasInput();
  var msg='';
  if(FP.pcBad&&!F.pc)msg=t('err.pc');
  else if(F.pc&&DB.pc4&&!DB.pc4[F.pc])msg=t('filters.unknownPc',{pc:F.pc});
  else if(F.pc)msg=t('filters.sortedPc',{place:DB.pc4[F.pc][2]});
  else msg=t('filters.sortedName');
  FP.pcmsg.textContent=msg;
  FP.pc.setAttribute('aria-invalid',FP.pcBad&&!F.pc?'true':'false');
  var n=(F.q?1:0)+(F.sec?1:0)+F.tr.length+F.ft.length+(F.den?1:0)+(F.pc?1:0)+(F.r?1:0);
  ['find','map'].forEach(function(k){var e=$(k+'-fsum');if(e)e.textContent=t('filters.summary')+(n?' '+t('filters.active',{n:n}):'')});
}
function mountForm(slot){
  ensureForm();
  if(FORM.parentNode!==slot){clear(slot);slot.appendChild(FORM)}
  syncForm();
}
function filterChanged(){
  syncNav();
  try{replaceUrl(U.view(VIEW,fQuery(VIEW==='map')))}catch(e){}
  syncForm();
  if(VIEW==='find')updateFind();else if(VIEW==='map')updateMap();
}
function syncNav(){
  var q=fQuery();
  $('t-find').setAttribute('href',U.view('find',q));
  $('t-map').setAttribute('href',U.view('map',q));
  var ml=$('map-list-link');if(ml)ml.setAttribute('href',U.view('find',q));
}

/* ---------- compare list ---------- */
var CMP=[],CMSG='';
function loadCmp(){
  try{var a=JSON.parse(localStorage.getItem(CMP_KEY)||'[]');
    if(Array.isArray(a))return a.filter(isId).map(function(x){return x.toUpperCase()}).slice(0,4)}catch(e){}
  return [];
}
function saveCmp(){try{localStorage.setItem(CMP_KEY,JSON.stringify(CMP))}catch(e){}}
function say(tx){var l=$('live');if(l){l.textContent='';setTimeout(function(){l.textContent=tx},30)}}
function cmpToggle(s){
  var i=CMP.indexOf(s.id);CMSG='';
  if(i>-1){CMP.splice(i,1);say(t('cmp.removed',{name:s.name}))}
  else{
    if(CMP.length>=4){CMSG=t('cmp.max')}
    else{
      var g=CMP.length?BYID[CMP[0]]:null;
      if(g&&grpOf(g)!==grpOf(s))CMSG=t(grpOf(g)==='vo'?'cmp.mixedVo':'cmp.mixedPo');
      else{CMP.push(s.id);say(t('cmp.added',{name:s.name}))}
    }
    if(CMSG)say(CMSG);
  }
  saveCmp();syncCmp();
}
function cmpBtn(s){
  var b=h('button',{class:'chip cmp',type:'button','data-cmp':s.id,onclick:function(){cmpToggle(s)}});
  cmpLabel(b,s);return b;
}
function cmpLabel(b,s){
  var on=CMP.indexOf(s.id)>-1;clear(b);
  b.appendChild(document.createTextNode(t(on?'cmp.in':'cmp.add')));
  b.appendChild(h('span',{class:'sr',text:' '+t(on?'cmp.pressRemove':'cmp.forName',{name:s.name})}));
  b.classList.toggle('on',on);
}
function syncCmp(){
  var bs=document.querySelectorAll('button[data-cmp]'),i,s;
  for(i=0;i<bs.length;i++){s=BYID[bs[i].getAttribute('data-cmp')];if(s)cmpLabel(bs[i],s)}
  renderCbar();
}
function renderCbar(){
  var bar=$('cbar');clear(bar);
  bar.setAttribute('aria-label',t('cmp.listAria'));
  if(!CMP.length||VIEW==='compare'){bar.hidden=true;document.body.classList.remove('has-cbar');return}
  bar.hidden=false;document.body.classList.add('has-cbar');
  var left=h('div',null,[h('b',{text:t('cmp.count',{n:CMP.length})})]);
  if(CMSG)left.appendChild(h('div',{style:'font-size:.88rem',text:CMSG}));
  else if(CMP.length<2)left.appendChild(h('div',{style:'font-size:.88rem',text:t('cmp.addOne')}));
  var acts=h('div',{class:'acts'});
  if(CMP.length>=2)acts.appendChild(h('a',{class:'btn',href:U.compare(CMP),text:t('cmp.go')}));
  acts.appendChild(h('button',{class:'btn sec',type:'button',text:t('cmp.clear'),onclick:function(){CMP=[];CMSG='';saveCmp();say(t('cmp.cleared'));syncCmp()}}));
  bar.appendChild(h('div',{class:'in'},[left,acts]));
}

/* ---------- lazy detail files ---------- */
var DET={po:null,vo:null,insp:null,p:{}};
function loadJson(key,url){
  if(DET.p[key])return DET.p[key];
  DET.p[key]=fetch(url).then(function(r){if(!r.ok)throw new Error(key);return r.json()}).then(function(j){
    j=j&&j.schools&&typeof j.schools==='object'?j:null;DET[key]=j;return j;
  }).catch(function(){DET[key]=null;return null});
  return DET.p[key];
}
function loadDetail(grp){return Promise.all([loadJson(grp,'data/detail_'+grp+'.json'),loadJson('insp','data/inspection.json')])}
function detOf(s){var d=DET[grpOf(s)];return d&&d.schools&&Object.prototype.hasOwnProperty.call(d.schools,s.id)?d.schools[s.id]:null}
function inspOf(s){var d=DET.insp;return d&&d.schools&&Object.prototype.hasOwnProperty.call(d.schools,s.id)?d.schools[s.id]:null}
function detYear(grp,key){var d=DET[grp];return d&&d.years&&d.years[key]!=null?String(d.years[key]):''}

/* ---------- Find view ---------- */
var FOUND=[],shown=0;
function findRow(r){
  var s=r.s,main=h('div');
  main.appendChild(h('a',{class:'nm',href:U.school(s.id),text:s.name}));
  main.appendChild(h('div',{class:'mt',text:[r.d!=null?secShort(s):null,s.city,s.mun&&s.mun!==s.city?s.mun:null,s.denT,pupilsText(s)].filter(Boolean).join(' · ')}));
  if(s.sec==='vo')main.appendChild(h('div',{style:'margin-top:5px'},trackBadges(s)));
  var fc=featChips(s);if(fc)main.appendChild(fc);
  main.appendChild(h('div',{class:'rowact'},cmpBtn(s)));
  var left=r.d!=null?distCell(r,s):h('div',{class:'kt',text:secShort(s)});
  return h('li',{class:'sch',style:'list-style:none'},[left,main]);
}
function viewGate(out){
  if(DB.status==='loading'){clear(out);out.appendChild(loadingBox());return false}
  if(DB.status==='error'){clear(out);out.appendChild(errorBox());return false}
  return true;
}
function updateFind(){
  var out=$('find-out');
  if(!viewGate(out)){clear($('find-form'));return}
  mountForm($('find-form'));
  clear(out);
  FOUND=runFilter();shown=0;
  var hd=h('div',{class:'res-h'},[h('p',{role:'status','aria-live':'polite',style:'font-weight:700',text:FOUND.length===0?t('find.none'):t('find.count',{n:FOUND.length})})]);
  hd.appendChild(h('a',{href:U.view('map',fQuery()),text:t('find.onMap')}));
  out.appendChild(hd);
  if(!FOUND.length){
    out.appendChild(h('div',{class:'empty',text:t('find.empty')}));
    return;
  }
  var card=h('div',{class:'list-card'});
  var ul=h('ul',{style:'padding:0;margin:0',id:'find-list'});card.appendChild(ul);
  out.appendChild(card);
  var more=h('button',{class:'btn sec more',type:'button',id:'find-more'});
  out.appendChild(more);
  function page(focusFirst){
    var end=Math.min(FOUND.length,shown+PAGE),first=null,i,li;
    for(i=shown;i<end;i++){li=findRow(FOUND[i]);if(!first)first=li;ul.appendChild(li)}
    shown=end;
    if(shown>=FOUND.length)more.hidden=true;
    else{more.hidden=false;more.textContent=t('btn.more',{n:Math.min(PAGE,FOUND.length-shown),left:FOUND.length-shown})}
    if(focusFirst&&first){var a=first.querySelector('a');if(a)a.focus()}
  }
  more.addEventListener('click',function(){page(true)});
  page(false);
  out.appendChild(h('p',{class:'note',text:t('find.note')}));
}

/* ---------- Map view ---------- */
var MAP={map:null,group:null,pcl:null,loading:null,pal:null,focus:null};
var MAPFOCUS='';
var LEAF_CSS='https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css';
var LEAF_JS='https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js';
function loadLeaflet(){
  if(window.L&&window.L.map)return Promise.resolve();
  if(MAP.loading)return MAP.loading;
  MAP.loading=new Promise(function(res,rej){
    var l=document.createElement('link');l.rel='stylesheet';l.href=LEAF_CSS;l.integrity='sha256-tXCrvaljxgtN5LT/Syb5Mm9T+yzPFGH98JVcoJT7JTk=';l.crossOrigin='anonymous';
    document.head.appendChild(l);
    var sc=document.createElement('script');sc.src=LEAF_JS;sc.integrity='sha256-XJrs/DDkVkUZ29zdzFOkGCJ9zHVo5hnpdi3c7HYJ7Uc=';sc.crossOrigin='anonymous';
    sc.onload=function(){res()};
    sc.onerror=function(){MAP.loading=null;rej(new Error('leaflet'))};
    document.head.appendChild(sc);
  });
  return MAP.loading;
}
function readPal(){
  var cs=getComputedStyle(document.documentElement);
  function v(n){return cs.getPropertyValue(n).trim()||'#888'}
  return {po:v('--c-bo'),sbo:v('--c-wo'),pro:v('--c-pro'),vbk:v('--c-vbk'),vgt:v('--c-vgt'),havo:v('--c-havo'),vwo:v('--c-vwo'),unk:v('--c-mbo'),pc:v('--ink')};
}
var MAP_LEG=['po','sbo','pro','vbk','vgt','havo','vwo','unk'];
function mapGroup(s){
  if(s.sec==='po'||s.sec==='sbo')return s.sec;
  var tr=s.tracks||0;
  if(tr&64)return 'vwo';if(tr&32)return 'havo';if(tr&24)return 'vgt';if(tr&6)return 'vbk';if(tr&1)return 'pro';
  return 'unk';
}
function mkMarker(s){
  if(s.mk)return s.mk;
  var g=mapGroup(s);
  var m=L.circleMarker([s.lat,s.lon],{radius:s.sec==='vo'?6:5,color:'#ffffff',weight:1,opacity:.9,fillColor:MAP.pal[g],fillOpacity:.88});
  m._g=g;
  m.on('click',function(){openPop(s)});
  s.mk=m;return m;
}
function openPop(s){
  var n=h('div',{class:'pop'});
  n.appendChild(h('b',{text:s.name}));
  n.appendChild(h('span',{text:secLong(s)+(s.city?', '+s.city:'')}));
  var pu=pupilsText(s);if(pu)n.appendChild(h('span',{text:pu}));
  n.appendChild(h('div',{class:'rowact'},[h('a',{href:U.school(s.id),text:t('map.openProfile')}),cmpBtn(s)]));
  L.popup({maxWidth:260,autoPanPadding:[20,20]}).setLatLng([s.lat,s.lon]).setContent(n).openOn(MAP.map);
}
function restyleMap(){
  if(!MAP.map)return;
  MAP.pal=readPal();
  for(var i=0;i<ALL.length;i++){var m=ALL[i].mk;if(m)m.setStyle({fillColor:MAP.pal[m._g]})}
  if(MAP.pcl)MAP.pcl.setStyle({color:MAP.pal.pc,fillColor:MAP.pal.pc});
  var lg=document.querySelectorAll('#map-legend i');
  for(var j=0;j<lg.length&&j<MAP_LEG.length;j++)lg[j].style.background=MAP.pal[MAP_LEG[j]];
}
if(window.matchMedia){
  try{window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change',function(){setTimeout(restyleMap,50)})}catch(e){}
}
function resetMap(){
  if(MAP.map){try{MAP.map.remove()}catch(e){}MAP.map=null;MAP.group=null;MAP.pcl=null}
  var o=$('map-out');if(o)clear(o);
}
function mapSkeleton(out){
  if($('mapel'))return;
  clear(out);
  out.appendChild(h('p',{class:'mapnote',id:'map-status',role:'status','aria-live':'polite'}));
  var lg=h('ul',{class:'legend',id:'map-legend','aria-label':t('map.legendAria')});
  MAP_LEG.forEach(function(x){lg.appendChild(h('li',null,[h('i',{'aria-hidden':'true'}),t('map.leg.'+x)]))});
  out.appendChild(lg);
  out.appendChild(h('div',{class:'mapwrap'},h('div',{id:'mapel',role:'application','aria-label':t('map.aria')})));
  out.appendChild(h('p',{class:'mapnote',text:t('map.note')}));
  out.appendChild(h('p',{class:'src',text:t('map.credit')}));
}
function updateMap(){
  var out=$('map-out');
  if(!viewGate(out)){clear($('map-form'));return}
  mountForm($('map-form'));
  mapSkeleton(out);
  var st=$('map-status');
  if(!MAP.map)st.textContent=t('map.loading');
  loadLeaflet().then(function(){
    if(VIEW!=='map')return;
    if(!MAP.map){
      MAP.pal=readPal();
      MAP.map=L.map('mapel',{preferCanvas:true,zoomSnap:0.5,minZoom:6,maxBounds:[[50.4,2.4],[54.0,8.2]],maxBoundsViscosity:.8}).setView([52.15,5.3],7);
      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">'+esc(t('map.attrName'))+'</a> '+esc(t('map.attrTail'))}).addTo(MAP.map);
      restyleMap();
    }
    MAP.map.invalidateSize();
    drawMap();
  }).catch(function(){st.textContent=t('map.failed')});
}
function drawMap(){
  var res=runFilter(),pts=[],ms=[],noloc=0,i,s,st=$('map-status');
  for(i=0;i<res.length;i++){
    s=res[i].s;
    if(s.g===3||s.lat==null){noloc++;continue}
    ms.push(mkMarker(s));pts.push([s.lat,s.lon]);
  }
  var focus=MAPFOCUS&&BYID[MAPFOCUS]&&BYID[MAPFOCUS].lat!=null?BYID[MAPFOCUS]:null;
  if(focus&&ms.indexOf(mkMarker(focus))<0){ms.push(mkMarker(focus));pts.push([focus.lat,focus.lon])}
  if(MAP.group)MAP.map.removeLayer(MAP.group);
  MAP.group=L.layerGroup(ms).addTo(MAP.map);
  if(MAP.pcl){MAP.map.removeLayer(MAP.pcl);MAP.pcl=null}
  var pt=fPoint(),bounds=null;
  if(pt){
    MAP.pcl=(F.r?L.circle([pt[0],pt[1]],{radius:F.r*1000,color:MAP.pal.pc,fillColor:MAP.pal.pc,fillOpacity:.04,weight:2,dashArray:'6 6',interactive:false}):L.circleMarker([pt[0],pt[1]],{radius:7,color:MAP.pal.pc,fillColor:MAP.pal.pc,fillOpacity:.9,weight:2,interactive:false})).addTo(MAP.map);
    bounds=F.r?MAP.pcl.getBounds():L.latLng(pt[0],pt[1]).toBounds(8000);
  }else if(pts.length&&pts.length<ALL.length)bounds=L.latLngBounds(pts);
  st.textContent=t('map.shown',{n:ms.length})+(noloc?' '+t('map.noloc',{n:noloc}):'');
  if(focus){MAP.map.setView([focus.lat,focus.lon],15);openPop(focus);MAPFOCUS='';syncNav()}
  else if(bounds&&bounds.isValid())MAP.map.fitBounds(bounds,{padding:[24,24],maxZoom:14});
  else if(!pts.length&&!pt)MAP.map.setView([52.15,5.3],7);
}

/* ---------- profile helpers ---------- */
function sortYear(a,b){var x=String(a[0]),y=String(b[0]);return x<y?-1:x>y?1:0}
function psec(title,expl,kids,src){
  var sec=h('section',{class:'psec'},[h('h3',{text:title})]);
  if(expl)sec.appendChild(h('p',{class:'expl'},[h('b',{text:t('prof.whatMeans')}),expl]));
  kids.forEach(function(k){if(k)sec.appendChild(k)});
  if(src)sec.appendChild(h('p',{class:'dsrc',text:src}));
  return sec;
}
function duoSrc(whatKey,key){
  var y=dataYear(key);
  return t('prof.duoSrc',{what:t(whatKey)})+(y&&(y.range||y.date)?': '+(y.range||'')+(y.date?' '+t('prof.counted',{date:y.date}):''):'')+'.';
}
function kvRow(a,b){return h('div',{class:'r'},[h('span',{text:a}),h('span',{text:b})])}
function kmText(m){
  if(typeof m!=='number')return '';
  if(m<1000)return t('prof.underKm');
  return t('unit.km',{n:dec1(m/1000)});
}
function trendChart(pt){
  var rows=pt.filter(function(e){return Array.isArray(e)}).slice().sort(sortYear);
  if(rows.length<2)return null;
  var W=520,H=210,L0=52,R0=16,T0=16,B0=34,vals=[];
  rows.forEach(function(e){if(typeof e[1]==='number')vals.push(e[1])});
  if(vals.length<2)return null;
  var max=Math.max.apply(null,vals);if(max<=0)return null;
  var top=Math.ceil(max/10)*10||max;
  function X(i){return L0+(rows.length===1?0:i*(W-L0-R0)/(rows.length-1))}
  function Y(v){return T0+(H-T0-B0)*(1-v/top)}
  var svg=svgEl('svg',{'class':'trend',viewBox:'0 0 '+W+' '+H,role:'img','aria-label':t('prof.trend.aria',{list:rows.map(function(e){return e[0]+' '+valTxt(e[1],e[2])}).join(t('sep.list'))})});
  [0,top/2,top].forEach(function(v){
    svg.appendChild(svgEl('line',{'class':'gr',x1:L0,x2:W-R0,y1:Y(v),y2:Y(v)}));
    svg.appendChild(svgEl('text',{x:L0-6,y:Y(v)+4,'text-anchor':'end'},numF(Math.round(v))));
  });
  var d='',gap=true;
  rows.forEach(function(e,i){
    if(typeof e[1]!=='number'){gap=true;return}
    d+=(gap?'M':'L')+X(i).toFixed(1)+' '+Y(e[1]).toFixed(1)+' ';gap=false;
  });
  svg.appendChild(svgEl('path',{'class':'ln',d:d}));
  rows.forEach(function(e,i){
    if(typeof e[1]!=='number')return;
    var c=svgEl('circle',{'class':'pt',cx:X(i),cy:Y(e[1]),r:5});
    c.appendChild(svgEl('title',null,t('prof.trend.pt',{year:String(e[0]),v:valTxt(e[1],e[2])})));
    svg.appendChild(c);
  });
  var step=Math.ceil(rows.length/6);
  rows.forEach(function(e,i){
    if(i%step!==0&&i!==rows.length-1)return;
    svg.appendChild(svgEl('text',{x:X(i),y:H-8,'text-anchor':i===0?'start':i===rows.length-1?'end':'middle'},String(e[0])));
  });
  return svg;
}
function pupilsSection(s,d){
  var kids=[];
  var big=s.pupils==null?t('prof.pupils.notShown'):(s.pupils_lb?t('prof.pupils.bigAtLeast',{n:s.pupils}):numF(s.pupils));
  kids.push(h('div',{class:'big',text:big}));
  kids.push(h('p',{class:'note',style:'margin-top:4px',text:s.pupils==null?t('prof.pupils.noCount'):t('prof.pupils.total')+(s.pupils_lb?' '+t('prof.pupils.hiddenNote'):'')}));
  var pt=d&&Array.isArray(d.pt)?d.pt:null;
  if(pt){
    var ch=trendChart(pt);
    if(ch){
      kids.push(ch);
      var det=h('details',{style:'margin-top:6px'},[h('summary',{style:'cursor:pointer;font-weight:700',text:t('prof.pupils.byYear')})]);
      var tb=h('div',{class:'kv'});
      pt.slice().sort(sortYear).forEach(function(e){tb.appendChild(kvRow(String(e[0]),valTxt(e[1],e[2])))});
      det.appendChild(tb);kids.push(det);
    }
  }
  return psec(t('prof.pupils.title'),t('prof.pupils.expl'),kids,duoSrc('prof.pupils.srcWhat',s.sec==='vo'?'vo_pupils':'po_pupils'));
}
function adviceSection(s,d){
  var kids=[adviceBar(s.adv)];
  var at=d&&Array.isArray(d.at)?d.at.slice().sort(sortYear):null;
  if(at)at=at.filter(function(e){return Array.isArray(e)&&e[3]});
  if(at&&at.length>1){
    var det=h('details',{style:'margin-top:10px'},[h('summary',{style:'cursor:pointer;font-weight:700',text:t('prof.advice.earlier')})]);
    at.forEach(function(e){
      det.appendChild(h('div',{style:'margin-top:8px'},[h('b',{text:t('prof.advice.leavers',{y:typeof e[0]==='number'?e[0]+'-'+(e[0]+1):String(e[0])})}),adviceBar([e[1],e[2],e[3]])]));
    });
    kids.push(det);
  }
  return psec(t('prof.advice.title'),t('prof.advice.expl'),kids,duoSrc('prof.advice.srcWhat','po_advice'));
}
function testSection(s,d){
  if(!d||!Array.isArray(d.es)||!d.es.length)return null;
  var tb=h('table',{class:'prtab'},[h('tbody')]),b=tb.firstChild;
  d.es.forEach(function(e){
    if(!Array.isArray(e))return;
    b.appendChild(h('tr',null,[h('th',{scope:'row',text:String(e[0])}),h('td',{text:e[1]==null?t('prof.test.noAvg'):t('prof.test.avg',{v:String(e[1])})}),h('td',{text:e[2]==null?t('prof.test.few'):t('unit.pupils',{n:e[2]})})]));
  });
  var y=detYear('po','eindscore');
  return psec(t('prof.test.title'),t('prof.test.expl'),[tb,h('p',{class:'note',text:t('prof.test.note')})],t('prof.test.src')+(y?' '+y:'')+'.');
}
function distSection(s,d){
  if(!d||!Array.isArray(d.dm)||(d.dm[1]==null&&d.dm[0]==null))return null;
  var kids=[];
  if(d.dm[1]!=null)kids.push(kvRow(t('prof.dist.median'),kmText(d.dm[1])));
  if(d.dm[0]!=null)kids.push(kvRow(t('prof.dist.avg'),kmText(d.dm[0])));
  if(d.dm[2]!=null)kids.push(kvRow(t('prof.dist.counted'),numF(d.dm[2])));
  var y=detYear('po','dist');
  return psec(t('prof.dist.title'),t('prof.dist.expl'),[h('div',{class:'kv'},kids)],t('prof.dist.src')+(y?', '+y:'')+'.');
}
var TK_MAP={'PRO':['pro','pro'],'VMBO-B':['bb','bb'],'VMBO-K':['kb','kb'],'VMBO-GL/TL':['gt','tl'],'HAVO':['havo','havo'],'VWO':['vwo','vwo'],'BRUGJAAR':['bridge','ib']};
var TK_ORDER=['PRO','VMBO-B','VMBO-K','VMBO-GL/TL','HAVO','VWO','BRUGJAAR'];
function tkKeys(o){
  var keys=TK_ORDER.filter(function(k){return Object.prototype.hasOwnProperty.call(o,k)});
  Object.keys(o).forEach(function(k){if(keys.indexOf(k)<0)keys.push(k)});
  return keys;
}
function tkInfo(k){return Object.prototype.hasOwnProperty.call(TK_MAP,k)?[t('tk.'+TK_MAP[k][0]),TK_MAP[k][1]]:[k,'ib']}
function levelsSection(s,d){
  var kids=[];
  var tb=trackBadges(s);
  kids.push(h('div',null,tb.childNodes.length?tb:h('span',{class:'note',text:t('prof.levels.none')})));
  if(s.st)kids.push(h('p',{class:'note',text:t('prof.levels.st',{st:s.st})}));
  var tp=d&&d.tp&&typeof d.tp==='object'?d.tp:null;
  if(tp){
    var keys=tkKeys(tp),mx=1,lbk=Array.isArray(d.tpl)?d.tpl:[];
    keys.forEach(function(k){if(typeof tp[k]==='number'&&tp[k]>mx)mx=tp[k]});
    var box=h('div',{style:'margin-top:10px'},[h('b',{text:t('prof.levels.perLevel')})]);
    keys.forEach(function(k){
      var inf=tkInfo(k),v=tp[k];
      box.appendChild(h('div',{class:'hbar'},[h('span',{class:'tr t-'+inf[1],text:inf[0]}),
        h('span',{class:'tk'},typeof v==='number'?h('i',{class:'a-'+(inf[1]==='pro'?'pro':inf[1]==='bb'||inf[1]==='kb'?'vbk':inf[1]==='tl'?'vgt':inf[1]==='havo'?'havo':inf[1]==='vwo'?'vwo':'x'),style:'width:'+Math.max(2,Math.round(v/mx*100))+'%'}):null),
        h('span',{class:'nn',text:valTxt(v,lbk.indexOf(k)>-1)})]));
    });
    kids.push(box);
  }
  return psec(t('prof.levels.title'),t('prof.levels.expl'),
    kids.concat(tp&&Array.isArray(d.tpl)&&d.tpl.length?[h('p',{class:'note',text:t('prof.levels.atLeastNote')})]:[]),duoSrc('prof.levels.srcWhat','vo_pupils')+(tp?'':' '+t('prof.levels.fromPupilFile')));
}
function passSection(s,d){
  var pr=d&&d.pr&&typeof d.pr==='object'?d.pr:null,kids=[];
  if(pr){
    tkKeys(pr).forEach(function(k){
      var arr=pr[k];if(!Array.isArray(arr)||!arr.length)return;
      var inf=tkInfo(k),tb=h('table',{class:'prtab'},[h('caption',{class:'sr',text:t('prof.pass.caption',{level:inf[0]})}),h('tbody')]),b=tb.lastChild;
      arr.slice().sort(sortYear).forEach(function(e){
        if(!Array.isArray(e))return;
        var txt=e[2]==null?t('prof.pass.few'):t('exam.rowPass',{pct:Math.round(e[2]),n:e[1]})+(e[3]?' '+t('prof.pass.partial'):'')+(e[1]!=null&&e[1]<30?' '+t('prof.pass.small'):'');
        b.appendChild(h('tr',null,[h('th',{scope:'row',text:t('prof.pass.year',{y:String(e[0])})}),h('td',{text:txt})]));
      });
      kids.push(h('div',null,[h('span',{class:'tr t-'+inf[1],text:inf[0]}),tb]));
    });
  }
  if(!kids.length){
    if(!s.exam||!s.exam.length)return psec(t('prof.pass.title'),t('prof.pass.explShort'),[h('p',{class:'note',text:t('prof.pass.none')})],duoSrc('prof.pass.srcWhat','vo_exams'));
    kids.push(examLine(s));
  }
  return psec(t('prof.pass.title'),t('prof.pass.expl'),kids,duoSrc('prof.pass.srcWhat','vo_exams'));
}
function catchSection(s,d){
  if(!d||!Array.isArray(d.cm)||!d.cm.length)return null;
  var ul=h('ul',{class:'pcl'});
  d.cm.slice(0,12).forEach(function(e){
    if(!Array.isArray(e)||!/^[1-9]\d{3}$/.test(String(e[0])))return;
    var pc=String(e[0]),nm=DB.pc4&&DB.pc4[pc]?DB.pc4[pc][2]:'';
    ul.appendChild(h('li',null,h('a',{href:U.routePc(pc)},[pc+(nm?' '+nm:''),' ',h('small',{text:e[1]==null?t('val.fewer5'):(e[2]?t('unit.pupilsAtLeast',{n:e[1]}):t('unit.pupils',{n:e[1]}))})])));
  });
  var kids=[ul];
  var y=detYear('vo','catchment');
  if(typeof d.cmo==='number')kids.push(h('p',{class:'note',text:t('prof.catch.other',{pct:Math.round(d.cmo)})}));
  return psec(t('prof.catch.title'),t('prof.catch.expl'),kids,t('prof.catch.src')+(y?', '+y:'')+'.');
}
function inspSection(s){
  var r=inspOf(s),I=DET.insp,kids=[];
  var link=h('a',{href:'https://www.onderwijsinspectie.nl/',target:'_blank',rel:'noopener',text:t('prof.insp.linkText')});
  if(r&&typeof r.o==='string'){
    var box=h('div',{class:'insp'},[h('b',{text:r.o})]);
    var xk=(r.x&&typeof r.x==='object')?Object.keys(r.x).filter(function(k){return typeof r.x[k]==='string'}):[];
    if(xk.length)box.appendChild(h('div',{class:'note',style:'margin:2px 0 0',text:t('prof.insp.lowest')}));
    if(r.d)box.appendChild(h('div',{class:'note',style:'margin:2px 0 0',text:t('prof.insp.dated',{date:r.d})}));
    xk.forEach(function(k){box.appendChild(h('div',{class:'note',style:'margin:2px 0 0',text:k+': '+r.x[k]}))});
    kids.push(box);
    var srcA=I&&safeUrl(I.source_url)?h('a',{href:I.source_url,target:'_blank',rel:'noopener',text:I.source||t('od.source')}):(I&&I.source?I.source:'');
    kids.push(h('p',{class:'dsrc'},[t('prof.insp.source')+' ',srcA,I&&I.as_of?'. '+t('prof.insp.asOf',{date:I.as_of}):'',I&&I.licence?'. '+t('attr.licence',{licence:I.licence}).replace(/\.$/,''):'','.']));
  }else{
    kids.push(h('p',null,[t('prof.insp.none')+' ',link,'.']));
  }
  return psec(t('prof.insp.title'),t('prof.insp.expl'),kids,null);
}
function openDaysSection(s){
  var f=DB.feat&&DB.feat.schools&&DB.feat.schools[s.id],td=todayStart(),list=[];
  if(f&&Array.isArray(f.open_days))f.open_days.forEach(function(o){var d=odDate(o.date);if(d&&d>=td)list.push({o:o,d:d})});
  list.sort(function(a,b){return a.d-b.d});
  var kids=[];
  if(list.length){
    var ul=h('ul',{class:'ods',style:'padding:0'});
    list.forEach(function(x){
      var url=safeUrl(x.o.url),notes=odNote(x.o);
      var li=h('li',null,[h('b',{text:fmtDate(x.d)+': '}),odLabel(x.o.label,false)]);
      if(url){li.appendChild(document.createTextNode(' · '));li.appendChild(h('a',{href:url,target:'_blank',rel:'noopener',text:t('od.source')}))}
      if(notes.length)li.appendChild(h('small',{text:notes.join(' · ')}));
      ul.appendChild(li);
    });
    kids.push(ul);
  }else{
    kids.push(h('p',{text:t('prof.od.none')}));
  }
  var w=safeWeb(s.web);
  if(w)kids.push(h('p',null,[t('prof.od.check')+' ',h('a',{href:w,target:'_blank',rel:'noopener',text:t('prof.od.siteLink')}),'.']));
  return psec(t('prof.od.title'),t('prof.od.expl'),kids,t('prof.od.src')+(DB.feat&&DB.feat.generated?t('prof.od.collected',{date:String(DB.feat.generated).slice(0,10)}):'')+'.');
}
function nearbySection(s){
  if(s.g===3||s.lat==null)return null;
  var found=nearest(ALL,[s.lat,s.lon],function(x){return x.sec===s.sec&&x.id!==s.id}).slice(0,5);
  if(!found.length)return null;
  var ul=h('ul',{class:'nb-list'});
  found.forEach(function(r){
    ul.appendChild(h('li',null,[h('span',null,[h('a',{href:U.school(r.s.id),text:r.s.name}),h('div',{class:'note',style:'margin:0',text:[r.s.city,r.s.denT].filter(Boolean).join(' · ')})]),h('span',{class:'d',text:kmStr(r.d)})]));
  });
  return psec(t('prof.nb.title.'+s.sec),t('prof.nb.expl'),[ul],t('prof.nb.src'));
}

/* ---------- School view ---------- */
function renderSchool(id){
  var out=$('school-out');
  if(!viewGate(out))return;
  var s=BYID[id];
  clear(out);
  if(!s){
    out.appendChild(h('h2',{class:'vh',id:'h-school',tabindex:'-1',text:t('school.notFound')}));
    out.appendChild(h('p',null,[t('school.noCode')+' ',h('b',{text:id}),'. ',h('a',{href:U.view('find'),text:t('school.search')}),'.']));
    document.title=t('title.schoolNotFound');
    return;
  }
  document.title=t('title.school',{name:s.name});
  var grp=grpOf(s);
  build();
  loadDetail(grp).then(function(r){
    if(VIEW==='school'&&CUR_ID===id&&(r[0]||r[1]))build();
  });
  function build(){
    var d=detOf(s),sc=window.pageYOffset;
    clear(out);
    var ph=h('div',{class:'phead'});
    ph.appendChild(h('a',{class:'back',href:U.view('find',fQuery()),text:t('school.back')}));
    ph.appendChild(h('div',{class:'when',text:secLong(s)}));
    ph.appendChild(h('h2',{id:'h-school',tabindex:'-1',text:s.name}));
    ph.appendChild(h('p',{class:'addr',text:[s.addr,[s.pc&&s.pc.length===6?s.pc.slice(0,4)+' '+s.pc.slice(4):s.pc,s.city].filter(Boolean).join(' '),s.mun&&s.mun!==s.city?t('school.municipality',{mun:s.mun}):null].filter(Boolean).join(', ')}));
    ph.appendChild(h('p',{style:'margin:0 0 6px',text:t('school.denom',{den:s.denT})+(s.sec==='vo'&&s.isk?t('school.isk'):'')}));
    var fc=featChips(s);if(fc)ph.appendChild(fc);
    var lk=links(s,grp);
    var mapA=s.g===3||s.lat==null?null:h('a',{href:U.mapFocus(s.id),text:t('school.showMap')});
    if(mapA)lk.appendChild(mapA);
    ph.appendChild(lk);
    ph.appendChild(h('div',{class:'rowact'},cmpBtn(s)));
    if(s.g>0&&s.g<3)ph.appendChild(h('p',{class:'note',text:t('school.approx')}));
    out.appendChild(ph);
    var secs=[pupilsSection(s,d)];
    if(s.sec==='vo'){secs.push(levelsSection(s,d));secs.push(passSection(s,d));secs.push(catchSection(s,d))}
    else if(s.sec==='po'){secs.push(adviceSection(s,d));secs.push(testSection(s,d));secs.push(distSection(s,d))}
    else{secs.push(testSection(s,d));secs.push(distSection(s,d));secs.push(psec(t('prof.sbo.title'),t('prof.sbo.text'),[],null))}
    secs.push(inspSection(s));secs.push(openDaysSection(s));secs.push(nearbySection(s));
    var grid=h('div',{class:'pgrid'});
    secs.forEach(function(x){if(x)grid.appendChild(x)});
    out.appendChild(grid);
    out.appendChild(h('p',{class:'note',text:t('school.note')}));
    syncCmp();
    window.scrollTo(0,sc);
  }
}

/* ---------- Compare view ---------- */
function latestPass(d){
  var pr=d&&d.pr&&typeof d.pr==='object'?d.pr:null,box=h('div');
  if(!pr)return null;
  tkKeys(pr).forEach(function(k){
    var a=Array.isArray(pr[k])?pr[k].slice().sort(sortYear):[];if(!a.length)return;
    var e=a[a.length-1],inf=tkInfo(k);
    box.appendChild(h('div',null,[h('span',{class:'tr t-'+inf[1],text:inf[0]}),' ',e[2]==null?t('prof.pass.few'):t(e[3]?'cmp.passPartial':'cmp.passOk',{pct:Math.round(e[2]),n:e[1],y:String(e[0])})]));
  });
  return box.childNodes.length?box:null;
}
function compareRows(grp){
  var rows=[];
  function R(l,sm,fn){rows.push([t('cmp.row.'+l),sm?t('cmp.row.'+sm):'',fn])}
  R('type','',function(s){return secLong(s)});
  R('place','',function(s){return [s.city,s.mun&&s.mun!==s.city?'('+s.mun+')':''].filter(Boolean).join(' ')});
  R('den','',function(s){return s.denT});
  R('pupils','pupilsSm',function(s){return s.pupils==null?t('cmp.notShown'):valTxt(s.pupils,s.pupils_lb)});
  R('features','featuresSm',function(s){return featChips(s)||t('cmp.noneListed')});
  if(grp==='po'){
    R('advice','adviceSm',function(s){return s.sec==='sbo'?t('cmp.na'):adviceBar(s.adv)});
    R('test','testSm',function(s,d){
      if(!d||!Array.isArray(d.es)||!d.es.length)return t('cmp.noData');
      var b=h('div');d.es.forEach(function(e){if(Array.isArray(e))b.appendChild(h('div',{text:e[0]+': '+(e[1]==null?t('cmp.notShown'):e[1])+(e[2]==null?'':' '+t('cmp.nIs',{n:e[2]}))}))});return b;
    });
    R('home','homeSm',function(s,d){if(!d||!Array.isArray(d.dm))return t('cmp.noData');return d.dm[1]!=null?kmText(d.dm[1]):d.dm[0]!=null?t('cmp.avgSuffix',{v:kmText(d.dm[0])}):t('cmp.noData')});
  }else{
    R('levels','',function(s){var tb=trackBadges(s);return tb.childNodes.length?tb:t('cmp.notInData')});
    R('perLevel','',function(s,d){
      if(!d||!d.tp)return t('cmp.noData');
      var b=h('div');tkKeys(d.tp).forEach(function(k){b.appendChild(h('div',{text:tkInfo(k)[0]+': '+valTxt(d.tp[k],Array.isArray(d.tpl)&&d.tpl.indexOf(k)>-1)}))});return b;
    });
    R('exam','examSm',function(s,d){return latestPass(d)||(s.exam&&s.exam.length?examLine(s):t('cmp.noData'))});
  }
  R('insp','',function(s){
    var r=inspOf(s);if(!(r&&r.o))return t('cmp.noInsp');
    var xk=(r.x&&typeof r.x==='object')?Object.keys(r.x).filter(function(k){return typeof r.x[k]==='string'}):[];
    var d=r.d?' ('+r.d+')':'';
    if(!xk.length)return r.o+d;
    var b=h('div',null,[h('div',{text:t('cmp.inspLowest',{o:r.o})+d})]);
    xk.forEach(function(k){b.appendChild(h('div',{text:k+': '+r.x[k]}))});
    return b;
  });
  R('od','odSm',function(s){return openLine(s)||t('cmp.noOd')});
  return rows;
}
function renderCompare(ids){
  var out=$('compare-out');
  if(!viewGate(out))return;
  var list=[];
  ids.forEach(function(x){
    x=String(x).toUpperCase();
    if(!isId(x)||!BYID[x]||list.indexOf(x)>-1)return;
    if(list.length&&grpOf(BYID[list[0]])!==grpOf(BYID[x]))return;
    if(list.length<4)list.push(x);
  });
  if(ids.length&&(list.join()!==CMP.join())){CMP=list;saveCmp()}
  if(!ids.length)list=CMP.slice();
  clear(out);
  if(list.length<1){
    out.appendChild(h('p',null,[t('cmp.nothing')+' ',h('a',{href:U.view('find'),text:t('cmp.findLink')}),' '+t('cmp.nothing2')]));
    renderCbar();return;
  }
  var grp=grpOf(BYID[list[0]]);
  var schools=list.map(function(id){return BYID[id]});
  build();
  loadDetail(grp).then(function(r){if(VIEW==='compare'&&(r[0]||r[1]))build()});
  function build(){
    var sc=window.pageYOffset;
    clear(out);
    out.appendChild(h('p',{class:'resmeta',text:t(grp==='vo'?'cmp.metaVo':'cmp.metaPo')}));
    var table=h('table',{class:'cmp'});
    var hrw=h('tr',null,[h('th',{scope:'col'},h('span',{class:'sr',text:t('cmp.measure')}))]);
    schools.forEach(function(s){
      hrw.appendChild(h('th',{scope:'col'},[h('a',{href:U.school(s.id),text:s.name}),h('div',{class:'rowact'},h('button',{class:'chip cmp',type:'button',text:t('cmp.remove'),onclick:function(){
        CMP=CMP.filter(function(x){return x!==s.id});saveCmp();say(t('cmp.removed',{name:s.name}));
        navigate(CMP.length?U.compare(CMP):U.view('find'));
      }},h('span',{class:'sr',text:' '+s.name})))]));
    });
    table.appendChild(h('thead',null,hrw));
    var tb=h('tbody');
    compareRows(grp).forEach(function(row){
      var tr=h('tr');
      tr.appendChild(h('th',{scope:'row'},[row[0],row[1]?h('small',{text:row[1]}):null]));
      schools.forEach(function(s){
        var v=row[2](s,detOf(s)),td=h('td');
        if(v==null)v='';
        td.appendChild(typeof v==='string'?document.createTextNode(v):v);
        tr.appendChild(td);
      });
      tb.appendChild(tr);
    });
    table.appendChild(tb);
    out.appendChild(h('div',{class:'cmpscroll',id:'compare-table-wrap',tabindex:'0',role:'region','aria-label':t('cmp.tableAria')},table));
    var y=detYear(grp,'pupils');
    var nt=[t(grp==='vo'?'cmp.noteVo':'cmp.notePo',{y:y?t('cmp.noteYear',{y:y}):''})];
    if(grp==='po')nt.push(t('cmp.noteTests'));
    out.appendChild(h('p',{class:'note',text:nt.join(' ')}));
    var acts=h('div',{class:'ctrl'});
    if(schools.length<4)acts.appendChild(h('a',{class:'btn sec',style:'display:inline-flex;align-items:center;text-decoration:none',href:U.view('find'),text:t('cmp.addAnother')}));
    acts.appendChild(h('button',{class:'btn sec',type:'button',text:t('cmp.clearList'),onclick:function(){CMP=[];saveCmp();say(t('cmp.cleared'));navigate(U.view('find'))}}));
    out.appendChild(acts);
    renderCbar();
    window.scrollTo(0,sc);
  }
}

/* ================= router ================= */
function parseHash(){var r=parseRoute();r.q=parseQ(r.q);return r}
function refreshView(){
  if(VIEW==='find')updateFind();
  else if(VIEW==='map')updateMap();
  else if(VIEW==='school')renderSchool(CUR_ID);
  else if(VIEW==='compare')renderCompare(CUR_IDS);
  syncCmp();
}
var CUR_IDS=[];
function reducedMotion(){try{return window.matchMedia('(prefers-reduced-motion: reduce)').matches}catch(e){return false}}
/* view switches only ever move the page up to the tab bar (never down, never an instant jump unless motion is reduced) */
function toContentTop(){
  var top=document.querySelector('.mast').offsetHeight;
  if(window.pageYOffset>top)window.scrollTo({top:top,behavior:reducedMotion()?'auto':'smooth'});
}
function updateTabFade(){
  var n=$('nav');if(!n)return;
  var x=Math.abs(n.scrollLeft);
  n.classList.toggle('fade-start',x>2);
  n.classList.toggle('fade-end',x+n.clientWidth<n.scrollWidth-2);
}
function keepTabVisible(a){
  var n=$('nav');if(!a||!n)return;
  if(n.scrollWidth>n.clientWidth+2){
    var l=a.offsetLeft,r=l+a.offsetWidth,x=Math.abs(n.scrollLeft);
    if(RTL_LANGS.indexOf(LANG)<0&&(l<x||r>x+n.clientWidth))n.scrollLeft=Math.max(0,l-(n.clientWidth-a.offsetWidth)/2);
  }
  updateTabFade();
}
function router(keep){
  var r=parseHash(),v=r.view;
  if(VIEWS.indexOf(v)<0){v='route';try{replaceUrl(U.route())}catch(e){}}
  VIEW=v;
  document.body.setAttribute('data-view',v);
  VIEWS.forEach(function(x){$('p-'+x).hidden=(x!==v)});
  var tabOf=({school:'find'})[v]||v;
  TABS.forEach(function(tb){
    var a=$('t-'+tb);if(tb===tabOf)a.setAttribute('aria-current','page');else a.removeAttribute('aria-current');
  });
  document.title=t(has('title.'+v)&&v!=='school'?'title.'+v:'title.route');
  CMSG='';
  if(v==='route'){
    var qpc=parsePc(r.q.pc||'');
    if(qpc){
      state.pc=qpc;state.example=false;state.grp='';state.level='';state.chips=null;nPo=15;nVo=15;nIsk=10;save();
      $('pc').value=state.pc;
      $('ferr').textContent=AGE_RE.test(state.age)?'':t('err.age');
      try{replaceUrl(U.route())}catch(e){}
    }
    render();
  }else if(v==='find'||v==='map'){
    if(Object.keys(r.q).length)applyQuery(r.q);
    MAPFOCUS=(v==='map'&&isId(r.q.s||''))?String(r.q.s).toUpperCase():'';
    syncNav();
    if(v==='find')updateFind();else updateMap();
  }else if(v==='school'){
    CUR_ID=isId(r.arg)?r.arg.toUpperCase():'';
    renderSchool(CUR_ID);
  }else if(v==='compare'){
    CUR_IDS=String(r.arg||'').split(',').filter(Boolean);
    renderCompare(CUR_IDS);
  }
  syncNav();
  renderCbar();
  keepTabVisible($('t-'+tabOf));
  if(!FIRST&&!keep){
    toContentTop();
    var hdn={find:'h-find',map:'h-map',school:'h-school',compare:'h-compare',sources:'h-sources'}[v];
    var el=hdn&&$(hdn);if(!el)el=$('main');
    try{el.focus({preventScroll:true})}catch(e){}
  }
  FIRST=false;
  if(v==='faq')faqFocus(r.q.q);
}

/* ================= static text, language, form ================= */
function applyStatic(){
  qsa('[data-i18n]').forEach(function(e){e.textContent=t(e.getAttribute('data-i18n'))});
  qsa('[data-i18n-attr]').forEach(function(e){
    e.getAttribute('data-i18n-attr').split(';').forEach(function(pair){
      var i=pair.indexOf(':');if(i>0)e.setAttribute(pair.slice(0,i).trim(),t(pair.slice(i+1).trim()));
    });
  });
  var md=document.querySelector('meta[name="description"]');
  if(md)md.setAttribute('content',t('meta.description'));
}
function buildAgeOptions(){
  var sel=$('age'),cur=sel.value||state.age||'';
  clear(sel);
  sel.appendChild(h('option',{value:'',text:t('form.agePlaceholder')}));
  sel.appendChild(h('option',{value:'u4',text:t('form.ageU4')}));
  for(var a=4;a<=17;a++)sel.appendChild(h('option',{value:String(a),text:t('form.ageN',{age:String(a)})}));
  sel.appendChild(h('option',{value:'18',text:t('form.age18')}));
  sel.value=state.example?'':cur;
}
function renderLangSwitch(){
  var box=$('langsw');clear(box);
  if(SUPPORTED.length<2)return;
  var sel=h('select',{id:'lang-sel',class:'langsel',onchange:function(e){changeLang(e.target.value)}});
  SUPPORTED.forEach(function(c){sel.appendChild(h('option',{value:c,selected:c===LANG?true:null,text:(LANG_META[c]&&LANG_META[c].name)||c}))});
  box.appendChild(h('label',{class:'sr',for:'lang-sel',text:t('lang.label')}));
  box.appendChild(sel);
}
function renderAllText(){
  applyStatic();applyRoutes();buildAgeOptions();renderExamples();renderGlossary();renderSystem();renderFaq();renderSources();renderLangSwitch();
}
function changeLang(code){
  if(SUPPORTED.indexOf(code)<0||code===LANG)return;
  loadDict(code).then(function(d){
    try{localStorage.setItem(LS_LANG,code)}catch(e){}
    DICT=d;WARNED={};setLocaleVars(code);
    applyDen();
    if(DB.status==='ready')buildIndex();
    FORM=null;F.den='';resetMap();
    renderAllText();
    router(true);
  }).catch(function(){});
}
function initForm(){
  var sel=$('age'),pcEl=$('pc');
  $('f').addEventListener('submit',function(e){
    e.preventDefault();
    var err=$('ferr'),pc=parsePc(pcEl.value),age=sel.value;
    if(!AGE_RE.test(age)){err.textContent=t('err.age');sel.setAttribute('aria-invalid','true');sel.focus();return}
    sel.removeAttribute('aria-invalid');
    if(!pc){err.textContent=t('err.pc');pcEl.setAttribute('aria-invalid','true');pcEl.focus();return}
    pcEl.removeAttribute('aria-invalid');
    if(DB.pc4&&!DB.pc4[pc]){err.textContent=t('err.unknownPc',{pc:pc})}
    else err.textContent='';
    var changed=(state.age!==age||state.pc!==pc||state.example);
    state.age=age;state.pc=pc;state.example=false;
    if(changed){state.grp='';state.level='';state.chips=null}
    nPo=15;nVo=15;nIsk=10;preview=false;
    save();
    if(VIEW!=='route')navigate(U.route());else render();
    var rb=$('resbar');if(rb&&rb.scrollIntoView)rb.scrollIntoView({block:'start'});
  });
  pcEl.addEventListener('input',function(){pcEl.removeAttribute('aria-invalid')});
  sel.addEventListener('change',function(){sel.removeAttribute('aria-invalid')});
}
function startApp(){
  migrateStorage();
  state=loadState();CMP=loadCmp();
  var sel=$('age');
  renderAllText();
  sel.value=state.age;
  $('pc').value=state.pc;
  initForm();
  document.body.classList.remove('booting');
  var b=$('boot');if(b)b.hidden=true;
  window.addEventListener('hashchange',function(){router()});
  $('nav').addEventListener('scroll',updateTabFade,{passive:true});window.addEventListener('resize',updateTabFade);
  $('skip').addEventListener('click',function(e){e.preventDefault();$('main').focus()});
  var l=document.createElement('div');l.id='live';l.className='sr';l.setAttribute('role','status');l.setAttribute('aria-live','polite');document.body.appendChild(l);
  loadData();router();
}
function bootFail(){
  var b=$('boot');if(b){b.textContent=b.getAttribute('data-fail')||'The page text could not be loaded. Please reload.';b.hidden=false}
}
(function boot(){
  var code=pickLang();
  loadDict('en').then(function(en){
    EN=en;
    return code==='en'?en:loadDict(code).catch(function(){code='en';return en});
  }).then(function(d){
    DICT=d;setLocaleVars(code);startApp();
  }).catch(bootFail);
})();
})();
