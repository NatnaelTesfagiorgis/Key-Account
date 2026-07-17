# %%
from __future__ import annotations

import base64
import importlib.util
import json
import shutil
from pathlib import Path 

BASE_FOLDER = Path(r"C:\Users\Natnael.Tesfagiorgis\OneDrive - Swinkels\Desktop\python\Key Account")
DATA_SCRIPT = BASE_FOLDER / "build_ka_dashboard_data.py"
LOGO_FILE = BASE_FOLDER / "habesha_logo.png"
OUTPUT_HTML = BASE_FOLDER / "KA_Performance_Dashboard.html"
TEMP_DATA_FOLDER = BASE_FOLDER / "dashboard_data"


def load_data_builder():
    if not DATA_SCRIPT.exists():
        raise FileNotFoundError(f"Missing required file: {DATA_SCRIPT}")
    spec = importlib.util.spec_from_file_location("ka_data_builder", DATA_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module 


def logo_data_uri() -> str:
    if not LOGO_FILE.exists():
        return ""
    encoded = base64.b64encode(LOGO_FILE.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


HTML = r'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Key Account Performance Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0"></script>
<style>
:root{
  --navy:#0a172e;
  --navy2:#102341;
  --gold:#c98b08;
  --gold2:#f0a51a;
  --cream:#fff8ea;
  --bg:#f5f1e8;
  --card:#ffffff;
  --line:#e4d7bf;
  --line2:#efe4d2;
  --ink:#151515;
  --muted:#6b655c;
  --green:#16834a;
  --red:#c9362c;
  --amber:#d88400;
  --grey:#b8b8b8;
  --shadow:0 14px 34px rgba(10,23,46,.10);
  --shadow-soft:0 7px 20px rgba(10,23,46,.07);
}
*{box-sizing:border-box}
html{
  text-rendering:geometricPrecision;
  -webkit-font-smoothing:antialiased;
}
body{
  margin:0;
  font-family:"Segoe UI Variable Text","Segoe UI","Inter","Arial",sans-serif;
  font-size:14px;
  line-height:1.45;
  letter-spacing:.004em;
  background:
    radial-gradient(circle at top left, rgba(240,165,26,.16), transparent 30%),
    linear-gradient(180deg,#fffaf0 0%,#f5f1e8 48%,#f3eee4 100%);
  color:var(--ink);
}
.page{
  max-width:1840px;
  margin:auto;
  padding:16px;
}
.topbar{
  display:flex;
  align-items:center;
  gap:22px;
  min-height:92px;
  padding:14px 24px;
  border:1px solid rgba(255,255,255,.14);
  border-radius:22px;
  background:
    linear-gradient(120deg,var(--navy) 0%,var(--navy2) 58%,#473106 100%);
  box-shadow:var(--shadow);
}
.logo{
  width:190px;
  height:62px;
  object-fit:contain;
  border-right:2px solid rgba(240,165,26,.75);
  padding-right:22px;
  filter:drop-shadow(0 2px 3px rgba(0,0,0,.18));
}
.topbar h1{
  margin:0;
  font-family:"Segoe UI Variable Display","Segoe UI Semibold","Segoe UI",Arial,sans-serif;
  font-size:34px;
  font-weight:760;
  line-height:1.05;
  letter-spacing:-.7px;
  color:#fffaf0;
}
.filters{
  display:grid;
  grid-template-columns:1.1fr repeat(5,1fr) 150px;
  gap:12px;
  margin-top:14px;
  padding:14px;
  border:1px solid var(--line2);
  border-radius:18px;
  background:rgba(255,255,255,.92);
  box-shadow:var(--shadow-soft);
}
.filter label{
  display:block;
  margin-bottom:6px;
  font-size:10.5px;
  font-weight:850;
  letter-spacing:.085em;
  text-transform:uppercase;
  color:#5d4b2b;
}
.filter select,.filter input{
  width:100%;
  height:39px;
  padding:9px 11px;
  border:1px solid #d3c6b2;
  border-radius:10px;
  background:#fff;
  color:#202020;
  font:650 13px/1.2 "Segoe UI Variable Text","Segoe UI",Arial,sans-serif;
}
.filter select:focus,.filter input:focus{
  outline:3px solid rgba(201,139,8,.18);
  border-color:var(--gold);
}
.btn{
  border:0;
  border-radius:10px;
  padding:10px 16px;
  background:linear-gradient(135deg,var(--gold2),var(--gold));
  color:#fff;
  font:850 12px/1.2 "Segoe UI Variable Text","Segoe UI",Arial,sans-serif;
  letter-spacing:.025em;
  cursor:pointer;
  box-shadow:0 8px 16px rgba(201,139,8,.22);
  transition:transform .12s ease, box-shadow .12s ease, filter .12s ease;
}
.btn:hover{
  transform:translateY(-1px);
  box-shadow:0 10px 20px rgba(201,139,8,.28);
  filter:saturate(1.08);
}
.cards{
  display:grid;
  grid-template-columns:repeat(7,minmax(150px,1fr));
  gap:11px;
  margin-top:12px;
}
.card{
  min-height:138px;
  background:linear-gradient(180deg,#ffffff 0%,#fffdf8 100%);
  border:1px solid var(--line2);
  border-radius:18px;
  padding:16px 14px;
  text-align:center;
  box-shadow:var(--shadow-soft);
  position:relative;
  overflow:hidden;
}
.card:before{
  content:"";
  position:absolute;
  inset:0 0 auto 0;
  height:4px;
  background:linear-gradient(90deg,var(--navy),var(--gold2));
}
.card-title{
  font-size:10.5px;
  font-weight:850;
  line-height:1.25;
  letter-spacing:.08em;
  text-transform:uppercase;
  color:#4f4129;
}
.card-value{
  margin:11px 0 6px;
  font-family:"Segoe UI Variable Display","Segoe UI Semibold","Segoe UI",Arial,sans-serif;
  font-size:32px;
  font-weight:820;
  line-height:1;
  letter-spacing:-.55px;
}
.card-sub{
  min-height:18px;
  font-size:11.5px;
  font-weight:600;
  color:#5c5850;
}
.progress{
  height:6px;
  border-radius:999px;
  background:#ece5d8;
  margin-top:15px;
  overflow:hidden;
}
.progress span{
  display:block;
  height:100%;
  border-radius:999px;
}
.grid3{
  display:grid;
  grid-template-columns:1.12fr 1.08fr 1fr;
  gap:12px;
  margin-top:12px;
}
.panel{
  background:rgba(255,255,255,.96);
  border:1px solid var(--line2);
  border-radius:18px;
  padding:16px;
  min-height:318px;
  box-shadow:var(--shadow-soft);
}
.panel h2,.table-title{
  margin:0 0 12px;
  font-family:"Segoe UI Variable Display","Segoe UI Semibold","Segoe UI",Arial,sans-serif;
  font-size:13px;
  font-weight:850;
  letter-spacing:.06em;
  text-transform:uppercase;
  color:var(--navy);
}
.chart{height:265px}
.table-panel{
  margin-top:12px;
  background:rgba(255,255,255,.97);
  border:1px solid var(--line2);
  border-radius:18px;
  overflow:hidden;
  box-shadow:var(--shadow-soft);
}
.toolbar{
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:12px;
  padding:12px 16px;
  border-bottom:1px solid var(--line2);
  background:linear-gradient(90deg,#fffdf8,#fff5df);
}
.picker{
  display:flex;
  align-items:center;
  gap:8px;
}
.picker input{
  width:190px;
  padding:8px 10px;
  border:1px solid #d8cdbb;
  border-radius:9px;
}
.table-wrap{
  overflow:auto;
  max-height:480px;
}
.manager-table-wrap{max-height:540px}
table{
  width:100%;
  border-collapse:separate;
  border-spacing:0;
  white-space:nowrap;
  font-family:"Segoe UI Variable Text","Segoe UI","Arial",sans-serif;
  font-size:11.8px;
  font-variant-numeric:tabular-nums;
}
th{
  position:sticky;
  top:0;
  z-index:2;
  background:linear-gradient(180deg,var(--navy2),var(--navy));
  color:#fff8ea;
  padding:10px 9px;
  border-bottom:1px solid rgba(255,255,255,.10);
  border-right:1px solid rgba(255,255,255,.08);
  text-align:center;
  font-size:10.5px;
  font-weight:850;
  line-height:1.22;
  letter-spacing:.045em;
  text-transform:uppercase;
}
td{
  padding:9px 10px;
  border-bottom:1px solid #efe5d5;
  border-right:1px solid #f2eadf;
  text-align:right;
  font-weight:580;
  color:#252525;
  background:#fff;
}
tbody tr:nth-child(even) td{background:#fffdf8}
td.left{text-align:left;font-weight:650;color:#1d1d1d}
tr:hover td{background:#fff5df}
.good{color:var(--green);font-weight:850}
.watch{color:#b86f00;font-weight:850}
.bad{color:var(--red);font-weight:850}
.positive{color:var(--green);font-weight:850}
.negative{color:var(--red);font-weight:850}
.pill{
  display:inline-block;
  min-width:58px;
  padding:4px 10px;
  border-radius:999px;
  font-weight:850;
  text-align:center;
}
.pill.good{background:#e8f6ee;color:var(--green)}
.pill.watch{background:#fff2d4;color:#b56a00}
.pill.bad{background:#fde9e7;color:var(--red)}
.warning{
  display:none;
  margin-top:12px;
  padding:10px 14px;
  background:#fff7e6;
  border:1px solid #f0d699;
  border-radius:12px;
  color:#78530b;
  font-size:12px;
  font-weight:600;
}
.footer{
  text-align:center;
  color:var(--muted);
  font-size:11px;
  font-weight:550;
  padding:15px;
}
canvas{image-rendering:auto}
@media(max-width:1200px){
  .filters{grid-template-columns:repeat(3,1fr)}
  .cards{grid-template-columns:repeat(3,1fr)}
  .grid3{grid-template-columns:1fr}
}
</style>
</head>
<body>
<div class="page">
<header class="topbar"><img class="logo" src="__LOGO__" alt="Habesha"><h1>Key Account Performance Dashboard</h1></header>
<section class="filters">
<div class="filter"><label>Date / Period</label><select id="period"><option value="MTD">MTD</option><option value="YTD">YTD</option></select></div>
<div class="filter"><label>KA Manager</label><select id="manager"></select></div>
<div class="filter"><label>Segment</label><select id="segment"></select></div>
<div class="filter"><label>Outlet</label><select id="outlet"></select></div>
<div class="filter"><label>SKU</label><select id="sku"></select></div>
<div class="filter"><label>Category</label><select id="category"></select></div>
<button id="clear" class="btn">↻ Clear Filters</button>
</section>
<div id="warning" class="warning"></div>

<section id="cards" class="cards"></section>

<section class="grid3">
  <article class="panel"><h2>Volume vs Target by KA Manager</h2><div class="chart"><canvas id="managerVolume"></canvas></div></article>
  <article class="panel"><h2>Visits by KA Manager</h2><div class="chart"><canvas id="managerVisits"></canvas></div></article>
  <article class="panel"><h2>Execution by KA Manager</h2><div class="chart"><canvas id="managerExecution"></canvas></div></article>
</section>

<section class="grid3">
  <article class="panel"><h2>Fridge Prod. by KA Manager</h2><div class="chart"><canvas id="managerFridge"></canvas></div></article>
  <article class="panel"><h2>Fridge Prod. Breakdown</h2><div class="chart"><canvas id="fridgeBreakdown"></canvas></div></article>
  <article class="panel"><h2>Volume Summary</h2><div class="chart"><canvas id="volumeSummary"></canvas></div></article>
</section>

<section class="table-panel">
  <div class="toolbar">
    <strong class="table-title">KA Manager Vol. Perf.</strong>
    <button id="exportManager" class="btn">⇩ Export</button>
  </div>
  <div class="table-wrap manager-table-wrap"><table id="managerTable"></table></div>
</section>

<section class="table-panel">
  <div class="toolbar">
    <strong class="table-title">Outlet Vol. Perf.</strong>
    <button id="exportOutlet" class="btn">⇩ Export</button>
  </div>
  <div class="table-wrap manager-table-wrap"><table id="outletTable"></table></div>
</section>

<section class="table-panel">
  <div class="toolbar">
    <strong class="table-title">Zero-Sales Outlets</strong>
    <button id="exportZeroSales" class="btn">⇩ Export</button>
  </div>
  <div class="table-wrap manager-table-wrap"><table id="zeroSalesTable"></table></div>
</section>

<div id="footer" class="footer"></div>
</div>
<script>
const D=__DATA__;
Chart.register(ChartDataLabels);
Chart.defaults.font.family='"Segoe UI","Arial",sans-serif';
Chart.defaults.font.size=11;
Chart.defaults.font.weight='600';
Chart.defaults.color='#2f2f2f';
Chart.defaults.devicePixelRatio=Math.max(window.devicePixelRatio||1,2);
Chart.defaults.plugins.legend.position='top';
Chart.defaults.plugins.legend.align='center';
Chart.defaults.plugins.legend.labels.usePointStyle=true;
Chart.defaults.plugins.legend.labels.boxWidth=8;
Chart.defaults.plugins.legend.labels.padding=16;
Chart.defaults.plugins.tooltip.backgroundColor='rgba(23,23,23,.92)';
Chart.defaults.plugins.tooltip.titleFont={weight:'700',size:12};
Chart.defaults.plugins.tooltip.bodyFont={weight:'600',size:12};
Chart.defaults.plugins.tooltip.padding=10;
Chart.defaults.plugins.tooltip.cornerRadius=8;

const F=D.facts;
const GOLD="#0f2a4a", GREY="#d7c6a3", GREEN="#1a8f5a", RED="#c9362c";
let charts={};

const LAST=new Date(D.meta.lastDataDate+"T00:00:00");
const MONTH_START=new Date(LAST.getFullYear(),LAST.getMonth(),1);
const YEAR_START=new Date(LAST.getFullYear(),0,1);

const num=(v,d=0)=>v==null||!Number.isFinite(Number(v))?"—":Number(v).toLocaleString(undefined,{maximumFractionDigits:d});
const pct=v=>v==null||!Number.isFinite(Number(v))?"—":Math.round(Number(v)*100)+"%";
const fd=v=>!v?"—":new Date(v+"T00:00:00").toLocaleDateString("en-GB",{day:"2-digit",month:"short",year:"numeric"});
const dateObj=v=>new Date(v+"T00:00:00");
const div=(a,b)=>b? a/b:null;
const cap=v=>v==null?null:Math.max(0,Math.min(v,1));
const sum=(rows,key)=>rows.reduce((a,r)=>a+(Number(r[key])||0),0);

function fill(id,vals,label=v=>v,value=v=>v){
  const e=document.getElementById(id);
  if(!e) return;
  e.innerHTML='<option value="ALL">All</option>';
  vals.forEach(v=>{const o=document.createElement("option");o.value=value(v);o.textContent=label(v);e.appendChild(o)});
}

fill("manager",D.filters.kaManagers);
fill("segment",D.filters.segments);
fill("outlet",D.filters.outlets,v=>v["Outlet ID"]+" — "+v["Outlet Name"],v=>v["Outlet ID"]);
fill("sku",D.filters.skus);
fill("category",D.filters.categories);

function state(){
  return {
    period:document.getElementById("period").value,
    manager:document.getElementById("manager").value,
    segment:document.getElementById("segment").value,
    outlet:document.getElementById("outlet").value,
    sku:document.getElementById("sku").value,
    category:document.getElementById("category").value
  };
}

function inRange(v,start,end){const d=dateObj(v); return d>=start && d<=end}
function monthEnd(d){return new Date(d.getFullYear(),d.getMonth()+1,0)}
function monthStartFromString(v){const d=dateObj(v); return new Date(d.getFullYear(),d.getMonth(),1)}
function periodBounds(period){return {start:period==="YTD"?YEAR_START:MONTH_START,end:LAST}}
function calendarRows(start,end){return F.calendar.filter(r=>inRange(r.Date,start,end))}
function workingDays(start,end){return calendarRows(start,end).filter(r=>r["Is Working Day"]===true).length}
function elapsedWorkingDays(){return workingDays(MONTH_START,LAST)}
function fullMonthWorkingDays(){return workingDays(MONTH_START,monthEnd(MONTH_START))}
function remainingWorkingDays(){const t=new Date(LAST);t.setDate(t.getDate()+1);return workingDays(t,monthEnd(LAST))}
function daysInPeriod(start,end){return Math.max(1,Math.round((end-start)/86400000)+1)}

function baseMatch(r,s){
  return (s.manager==="ALL"||r["KA Manager"]===s.manager)
    && (s.segment==="ALL"||r["Segment"]===s.segment)
    && (s.outlet==="ALL"||r["Outlet ID"]===s.outlet);
}
function salesMatch(r,s){
  return baseMatch(r,s)
    && (s.sku==="ALL"||r["SKU"]===s.sku)
    && (s.category==="ALL"||r["Category"]===s.category);
}
function targetMatch(r,s){
  return baseMatch(r,s)
    && (s.category==="ALL"||r["Category"]===s.category);
}
function selectedOutlets(s){return F.outlets.filter(r=>baseMatch(r,s)&&r["Is Active"]!==false)}
function salesRows(s,start,end){return F.sales.filter(r=>salesMatch(r,s)&&inRange(r.Date,start,end))}
function visitRows(s,start,end){return F.visits.filter(r=>baseMatch(r,s)&&inRange(r.Date,start,end))}
function executionRows(s,start,end){return F.execution.filter(r=>baseMatch(r,s)&&inRange(r.Date,start,end))}
function targetRows(s,start,end){
  if(s.sku!=="ALL") return [];
  return F.targets.filter(r=>{
    const m=monthStartFromString(r["Target Month"]);
    return targetMatch(r,s)
      && m>=new Date(start.getFullYear(),start.getMonth(),1)
      && m<=new Date(end.getFullYear(),end.getMonth(),1);
  });
}
function monthlyFactor(monthStart,periodEnd){
  const end=monthEnd(monthStart), capped=periodEnd<end?periodEnd:end;
  const total=workingDays(monthStart,end), elapsed=workingDays(monthStart,capped);
  return total?elapsed/total:0;
}
function phasedTargetTotal(rows,end){
  return rows.reduce((a,r)=>{
    const m=monthStartFromString(r["Target Month"]);
    const factor=(m.getFullYear()===end.getFullYear()&&m.getMonth()===end.getMonth())?monthlyFactor(m,end):1;
    return a+(Number(r["Full Month Target"])||0)*factor;
  },0);
}
function latestExecByOutlet(rows){
  const m=new Map();
  rows.forEach(r=>{const old=m.get(r["Outlet ID"]); if(!old||dateObj(r.Date)>dateObj(old.Date))m.set(r["Outlet ID"],r)});
  return [...m.values()];
}

function aggregateKPIs(s,period=s.period){
  const {start,end}=periodBounds(period);
  const outlets=selectedOutlets(s), ids=new Set(outlets.map(r=>r["Outlet ID"]));
  const sales=salesRows(s,start,end).filter(r=>ids.has(r["Outlet ID"]));
  const visits=visitRows(s,start,end).filter(r=>ids.has(r["Outlet ID"]));
  const exec=latestExecByOutlet(executionRows(s,start,end).filter(r=>ids.has(r["Outlet ID"])));
  const targets=targetRows(s,start,end).filter(r=>ids.has(r["Outlet ID"]));

  const actual=sum(sales,"Actual Volume");
  const target=s.sku==="ALL"?phasedTargetTotal(targets,end):null;
  const volumeAch=target?actual/target:null;
  const planned=sum(visits,"Planned Visits");
  const actualVisits=sum(visits,"Actual Visits");
  const jpGood=sum(visits,"JP Good Visits");
  const visitCompletion=div(actualVisits,planned);
  const jpAdherence=div(jpGood,actualVisits);
  const executionActual=exec.length?exec.reduce((a,r)=>a+(Number(r["Execution Actual"])||0),0)/exec.length:null;
  const executionTarget=exec.length?exec.reduce((a,r)=>a+(Number(r["Execution Target"])||0),0)/exec.length:(D.kpiTargets["Execution Standard"]||.85);
  const executionAch=div(executionActual,executionTarget);

  const fridgeOutlets=outlets.filter(r=>r["Has Fridge"]===true), fridgeIds=new Set(fridgeOutlets.map(r=>r["Outlet ID"]));
  const fridgeVolume=sales.filter(r=>fridgeIds.has(r["Outlet ID"])).reduce((a,r)=>a+(Number(r["Actual Volume"])||0),0);
  const fridgeProductivity=fridgeOutlets.length?fridgeVolume/(fridgeOutlets.length*daysInPeriod(start,end)):null;

  const values={
    "Volume":cap(volumeAch),
    "JP Adherence":cap(jpAdherence),
    "Visit Completion":cap(visitCompletion),
    "Execution Standard":cap(executionAch),
    "Fridge Productivity":cap(div(fridgeProductivity,D.kpiTargets["Fridge Productivity"]||1))
  };

  // Overall KPI is now driven only by KPI_Config.
  // A KPI contributes only when Included in Final KPI = Yes/TRUE/1.
  // Achievement is capped at 100% only for the weighted Overall KPI score.
  function isIncludedFinal(value){
    if(value===true) return true;
    const x=String(value??"").trim().toLowerCase();
    return ["yes","y","true","1","included"].includes(x);
  }
  function kpiConfigWeight(value){
    const w=Number(value);
    if(!Number.isFinite(w)) return null;
    return w>1 ? w/100 : w;
  }
  function normalizeKpiName(name){
    const x=String(name??"").trim().toLowerCase();
    if(["volume","volume achievement","shipment volume","sales volume","sales volume achievement"].includes(x)) return "Volume";
    if(["jp adherence","journey plan adherence","jp","plan adherence"].includes(x)) return "JP Adherence";
    if(["visit completion","visit completion rate","visits completion"].includes(x)) return "Visit Completion";
    if(["execution standard","execution","execution standard achievement"].includes(x)) return "Execution Standard";
    if(["fridge productivity","cold coverage","fridge","cooler productivity"].includes(x)) return "Fridge Productivity";
    return null;
  }

  let weighted=0,weights=0;
  F.kpiConfig.forEach(r=>{
    if(!isIncludedFinal(r["Included Final"])) return;
    const key=normalizeKpiName(r.KPI);
    const v=key ? values[key] : null;
    const w=kpiConfigWeight(r.Weight);
    if(v!=null && Number.isFinite(v) && w!=null && Number.isFinite(w)){
      weighted+=v*w;
      weights+=w;
    }
  });

  return {overall:weights?weighted/weights:null,actual,target,volumeAch,planned,actualVisits,visitCompletion,jpAdherence,fridgeProductivity,executionActual,executionTarget,executionAch,activeOutlets:outlets.length};
}

function renderCards(){
  const k=aggregateKPIs(state());

  function isIncludedFinalCard(value){
    if(value===true) return true;
    const x=String(value??"").trim().toLowerCase();
    return ["yes","y","true","1","included"].includes(x);
  }
  const cards=[
    {title:"Overall KPI",actual:k.overall,target:D.kpiTargets["Overall KPI"]||.8,format:"percent"},
    {title:"Volume Achievement",actual:k.volumeAch,target:D.kpiTargets.Volume||1,format:"percent",sub:`Actual: ${num(k.actual)} &nbsp; Target: ${num(k.target)}`},
    {title:"JP Adherence",actual:k.jpAdherence,target:D.kpiTargets["JP Adherence"]||.8,format:"percent"},
    {title:"Visit Completion",actual:k.visitCompletion,target:D.kpiTargets["Visit Completion"]||1,format:"percent"},
    {title:"Fridge Productivity",actual:k.fridgeProductivity,target:D.kpiTargets["Fridge Productivity"]||1,format:"decimal"},
    {title:"Active Outlets",actual:k.activeOutlets,target:null,format:"integer"},
    {title:"Execution Standard",actual:k.executionActual,target:k.executionTarget,format:"percent"}
  ];
  document.getElementById("cards").innerHTML=cards.map(c=>{
    const val=c.format==="percent"?pct(c.actual):c.format==="decimal"?num(c.actual,2):num(c.actual);
    const sub=c.sub??(c.target==null?"":`Target: ${c.format==="percent"?pct(c.target):num(c.target,2)}`);
    const ach=c.target&&c.actual!=null?Math.min(c.actual/c.target,1):0;
    const color=c.actual==null?GREY:(c.target&&c.actual>=c.target?GREEN:GOLD);
    return `<div class="card"><div class="card-title">${c.title}</div><div class="card-value" style="color:${color}">${val}</div><div class="card-sub">${sub}</div><div class="progress"><span style="width:${Math.max(0,ach*100)}%;background:${color}"></span></div></div>`;
  }).join("");
}

function kill(id){if(charts[id]){charts[id].destroy();delete charts[id]}}
function combo(id,rows,labelKey,aKey,tKey,hKey){
  kill(id);
  charts[id]=new Chart(document.getElementById(id),{
    type:"bar",
    data:{labels:rows.map(r=>r[labelKey]),datasets:[
      {
        label:"Actual",
        data:rows.map(r=>r[aKey]??0),
        backgroundColor:GOLD,
        borderColor:"#0a1f36",
        borderWidth:0,
        borderRadius:5,
        barPercentage:.78,
        categoryPercentage:.72,
        yAxisID:"y"
      },
      {
        label:"Target",
        data:rows.map(r=>r[tKey]??0),
        backgroundColor:GREY,
        borderColor:"#c8b790",
        borderWidth:0,
        borderRadius:5,
        barPercentage:.78,
        categoryPercentage:.72,
        yAxisID:"y"
      },
      {
        label:"Achievement %",
        data:rows.map(r=>r[hKey]==null?null:r[hKey]*100),
        type:"line",
        borderColor:GREEN,
        backgroundColor:GREEN,
        borderWidth:3,
        tension:.35,
        borderDash:[6,4],
        pointRadius:4,
        pointHoverRadius:5,
        pointBackgroundColor:"#ffffff",
        pointBorderColor:GREEN,
        pointBorderWidth:2,
        yAxisID:"y1"
      }
    ]},
    options:{
      responsive:true,
      maintainAspectRatio:false,
      plugins:{
        legend:{position:"top",align:"center"},
        datalabels:{
          display:c=>c.datasetIndex===2,
          formatter:v=>v==null?"":Math.round(v)+"%",
          anchor:"end",
          align:"top",
          offset:2,
          color:"#1f1f1f",
          font:{weight:"700",size:11}
        }
      },
      scales:{
        y:{beginAtZero:true,grid:{color:"#ece7dd"}},
        y1:{beginAtZero:true,position:"right",grid:{drawOnChartArea:false},ticks:{callback:v=>v+"%"}}
      }
    }
  });
}
function doughnut(id,labels,values){
  kill(id);
  charts[id]=new Chart(document.getElementById(id),{
    type:"doughnut",
    data:{labels,datasets:[{
      data:values,
      backgroundColor:["#1a8f5a","#d8b56a","#b94a3f"],
      borderColor:"#ffffff",
      borderWidth:3,
      hoverOffset:6
    }]},
    options:{
      responsive:true,
      maintainAspectRatio:false,
      cutout:"60%",
      plugins:{
        legend:{
          position:"bottom",
          align:"center",
          labels:{usePointStyle:true,boxWidth:8,padding:16}
        },
        datalabels:{
          formatter:(v,c)=>{const t=c.dataset.data.reduce((a,b)=>a+b,0);return t?Math.round(v/t*100)+"%":""},
          color:"#fff",
          font:{weight:"800",size:11}
        }
      }
    }
  });
}
function buildCharts(){
  const s=state(), {start,end}=periodBounds(s.period);
  const managers=[...new Set(selectedOutlets(s).map(r=>r["KA Manager"]||"Unassigned"))].sort();

  const volumeRows=managers.map(m=>{const k=aggregateKPIs({...s,manager:m},s.period);return {"KA Manager":m,Actual:k.actual,Target:k.target,Achievement:k.volumeAch}});
  combo("managerVolume",volumeRows,"KA Manager","Actual","Target","Achievement");

  const visitRowsByManager=managers.map(m=>{
    const ss={...s,manager:m}, rows=visitRows(ss,start,end);
    const planned=sum(rows,"Planned Visits"), actual=sum(rows,"Actual Visits");
    return {"KA Manager":m,Planned:planned,Actual:actual,Achievement:div(actual,planned)};
  });
  combo("managerVisits",visitRowsByManager,"KA Manager","Actual","Planned","Achievement");

  const execRows=managers.map(m=>{
    const ss={...s,manager:m};
    const exec=latestExecByOutlet(executionRows(ss,start,end));
    const actual=exec.length?exec.reduce((a,r)=>a+(Number(r["Execution Actual"])||0),0)/exec.length:null;
    const target=exec.length?exec.reduce((a,r)=>a+(Number(r["Execution Target"])||0),0)/exec.length:null;
    return {"KA Manager":m,Actual:actual,Target:target,Achievement:div(actual,target)};
  });
  combo("managerExecution",execRows,"KA Manager","Actual","Target","Achievement");

  const fridgeRows=managers.map(m=>{
    const ss={...s,manager:m}, k=aggregateKPIs(ss,s.period), t=D.kpiTargets["Fridge Productivity"]||1;
    return {"KA Manager":m,Actual:k.fridgeProductivity,Target:t,Achievement:div(k.fridgeProductivity,t)};
  });
  combo("managerFridge",fridgeRows,"KA Manager","Actual","Target","Achievement");

  const outlets=selectedOutlets(s).filter(r=>r["Has Fridge"]===true), ids=new Set(outlets.map(r=>r["Outlet ID"]));
  const sales=salesRows(s,start,end).filter(r=>ids.has(r["Outlet ID"]));
  const outletVol=new Map();sales.forEach(r=>outletVol.set(r["Outlet ID"],(outletVol.get(r["Outlet ID"])||0)+(Number(r["Actual Volume"])||0)));
  const days=daysInPeriod(start,end), counts={Productive:0,Underproductive:0,Inactive:0};
  outlets.forEach(o=>{const p=(outletVol.get(o["Outlet ID"])||0)/days;if(p>=1)counts.Productive++;else if(p>0)counts.Underproductive++;else counts.Inactive++});
  doughnut("fridgeBreakdown",["Productive","Underproductive","Inactive"],[counts.Productive,counts.Underproductive,counts.Inactive]);

  const k=aggregateKPIs(s,s.period);
  combo("volumeSummary",[{Metric:"Volume",Actual:k.actual,Target:k.target,Achievement:k.volumeAch}], "Metric","Actual","Target","Achievement");
}

function monthlyTargets(s){
  if(s.sku!=="ALL") return [];
  return F.targets.filter(r=>{
    const m=monthStartFromString(r["Target Month"]);
    return targetMatch(r,s) && m.getFullYear()===MONTH_START.getFullYear() && m.getMonth()===MONTH_START.getMonth();
  });
}
function mtdSales(s){return F.sales.filter(r=>salesMatch(r,s)&&inRange(r.Date,MONTH_START,LAST))}
function volumePerfRow(labelFields, s){
  const julyTarget=sum(monthlyTargets(s),"Full Month Target");
  const wdFull=fullMonthWorkingDays(), wdElapsed=elapsedWorkingDays(), wdRemaining=remainingWorkingDays();
  const mtdTarget=wdFull ? julyTarget*wdElapsed/wdFull : null;
  const actual=sum(mtdSales(s),"Actual Volume");
  const dailyTarget=wdFull ? julyTarget/wdFull : null;
  const actualRR=wdElapsed ? actual/wdElapsed : null;
  const remainingTarget=Math.max(julyTarget-actual,0);
  const expectedRR=wdRemaining ? remainingTarget/wdRemaining : null;
  const projected=(actualRR||0)*wdFull;
  return {
    ...labelFields,
    "July Target":julyTarget,
    "MTD Target":mtdTarget,
    "MTD Actual":actual,
    "% MTD Target Achieved":div(actual,mtdTarget),
    "% Monthly Target Achieved":div(actual,julyTarget),
    "Daily Target":dailyTarget,
    "Actual Run rate":actualRR,
    "Expected Daily required Run rate":expectedRR,
    "Variance Monthly (Actual Vs Target)":actual-julyTarget,
    "Closing RR (Cadence)":div(projected,julyTarget)
  };
}
function buildManagerRows(){
  const s=state();
  const managers=[...new Set(selectedOutlets(s).map(r=>r["KA Manager"]||"Unassigned"))].sort();
  const totalActual=sum(mtdSales(s),"Actual Volume");
  const rows=managers.map(manager=>{
    const row=volumePerfRow({"KA Manager":manager}, {...s,manager});
    row["Contri %"]=div(row["MTD Actual"],totalActual);
    return row;
  });
  if(s.manager==="ALL"&&s.segment==="ALL"&&s.outlet==="ALL"){
    const total=volumePerfRow({"KA Manager":"Grand Total"}, s);
    total["Contri %"]=1;
    rows.push(total);
  }
  return rows;
}
function buildOutletRows(){
  const s=state();
  const totalActual=sum(mtdSales(s),"Actual Volume");
  return selectedOutlets(s).map(o=>{
    const row=volumePerfRow({"KA Manager":o["KA Manager"],"Outlet Name":o["Outlet Name"],"Outlet ID":o["Outlet ID"]}, {...s,outlet:o["Outlet ID"]});
    row["Contri %"]=div(row["MTD Actual"],totalActual);
    return row;
  });
}
function buildZeroRows(){
  const s=state();
  const outletRows=buildOutletRows();
  return outletRows
    .filter(r=>(Number(r["MTD Actual"])||0)===0)
    .map(r=>({"KA Manager":r["KA Manager"],"Outlet Name":r["Outlet Name"],"Outlet ID":r["Outlet ID"]}));
}

const managerCols=[
  ["KA Manager","KA Manager","t"],
  ["Contri %","Contri %","p"],
  ["July Target","Jul Target","n"],
  ["MTD Target","MTD Target","n"],
  ["MTD Actual","MTD Actual","n"],
  ["% MTD Target Achieved","MTD Ach %","p"],
  ["% Monthly Target Achieved","Mon Ach %","p"],
  ["Daily Target","Daily Tgt","n1"],
  ["Actual Run rate","Actual RR","n1"],
  ["Expected Daily required Run rate","Req. RR","n1"],
  ["Variance Monthly (Actual Vs Target)","Mon Var.","n"],
  ["Closing RR (Cadence)","Closing RR","cadence"]
];
const outletCols=[
  ["KA Manager","KA Manager","t"],
  ["Outlet Name","Outlet","t"],
  ["Outlet ID","Outlet ID","t"],
  ["July Target","Jul Target","n"],
  ["MTD Target","MTD Target","n"],
  ["MTD Actual","MTD Actual","n"],
  ["% MTD Target Achieved","MTD Ach %","p"],
  ["% Monthly Target Achieved","Mon Ach %","p"],
  ["Daily Target","Daily Tgt","n1"],
  ["Actual Run rate","Actual RR","n1"],
  ["Expected Daily required Run rate","Req. RR","n1"],
  ["Variance Monthly (Actual Vs Target)","Mon Var.","n"],
  ["Closing RR (Cadence)","Closing RR","cadence"]
];
const zeroCols=[["KA Manager","KA Manager","t"],["Outlet Name","Outlet Name","t"],["Outlet ID","Outlet ID","t"]];

function cell(v,t){
  if(t==="cadence"){
    const c = v==null || !Number.isFinite(Number(v)) ? "bad" : (Number(v)>=1 ? "good" : (Number(v)>=0.9 ? "watch" : "bad"));
    return `<span class="pill ${c}">${pct(v)}</span>`;
  }
  if(t==="p")return pct(v);
  if(t==="n")return num(v,0);
  if(t==="n1")return num(v,1);
  return v??"—";
}
function table(id,rows,cols){
  document.getElementById(id).innerHTML=`<thead><tr>${cols.map(c=>`<th>${c[1]}</th>`).join("")}</tr></thead><tbody>${rows.map(r=>`<tr>${cols.map((c,i)=>{
    const varianceClass = c[0]==="Variance Monthly (Actual Vs Target)" ? ((Number(r[c[0]])||0)>=0 ? " positive" : " negative") : "";
    return `<td class="${tLeft(c[2])?"left":""}${varianceClass}">${cell(r[c[0]],c[2])}</td>`;
  }).join("")}</tr>`).join("")}</tbody>`;
}
function tLeft(t){return t==="t"}
let currentManagerRows=[], currentOutletRows=[], currentZeroRows=[];
function renderTables(){
  currentManagerRows=buildManagerRows();
  currentOutletRows=buildOutletRows();
  currentZeroRows=buildZeroRows();
  table("managerTable",currentManagerRows,managerCols);
  table("outletTable",currentOutletRows,outletCols);
  table("zeroSalesTable",currentZeroRows,zeroCols);
}
function csv(name,rows,cols){
  const q=v=>'"'+String(v??"").replaceAll('"','""')+'"';
  const out=[cols.map(c=>q(c[1])).join(","),...rows.map(r=>cols.map(c=>q(r[c[0]])).join(","))].join("\n");
  const b=new Blob(["\ufeff"+out],{type:"text/csv"});
  const a=document.createElement("a");a.href=URL.createObjectURL(b);a.download=name;a.click();URL.revokeObjectURL(a.href);
}
function refreshOutletOptions(){
  const s=state(), current=document.getElementById("outlet").value;
  const vals=F.outlets.filter(r=>(s.manager==="ALL"||r["KA Manager"]===s.manager)&&(s.segment==="ALL"||r["Segment"]===s.segment));
  fill("outlet",vals,v=>v["Outlet ID"]+" — "+v["Outlet Name"],v=>v["Outlet ID"]);
  if(vals.some(v=>v["Outlet ID"]===current))document.getElementById("outlet").value=current;
}
function renderAll(){renderCards();buildCharts();renderTables()}

document.getElementById("clear").onclick=()=>{["manager","segment","outlet","sku","category"].forEach(id=>document.getElementById(id).value="ALL");document.getElementById("period").value="MTD";refreshOutletOptions();renderAll()};
["period","outlet","sku","category"].forEach(id=>document.getElementById(id).onchange=renderAll);
["manager","segment"].forEach(id=>document.getElementById(id).onchange=()=>{refreshOutletOptions();renderAll()});
document.getElementById("exportManager").onclick=()=>csv("KA_Manager_Volume_Performance.csv",currentManagerRows,managerCols);
document.getElementById("exportOutlet").onclick=()=>csv("Outlet_Volume_Performance.csv",currentOutletRows,outletCols);
document.getElementById("exportZeroSales").onclick=()=>csv("Zero_Sales_Outlets.csv",currentZeroRows,zeroCols);

const notes=[];
if(D.meta.unmatchedProductRows)notes.push(`${D.meta.unmatchedProductRows} actual-sales rows have products not mapped in Product_MDM.`);
if(notes.length){const w=document.getElementById("warning");w.textContent=notes.join(" ");w.style.display="block"}
document.getElementById("footer").textContent=`Generated ${D.meta.generatedAt} • Last data date ${D.meta.lastDataDate} • Sales targets phased by working days • Fridge productivity uses all calendar days`;
renderAll();
</script>
</body></html>'''


def generate_html() -> Path:
    builder = load_data_builder()
    payload = builder.build_dashboard_extract()

    # The final deliverable is one HTML file, so remove intermediate JSON/CSV files.
    if TEMP_DATA_FOLDER.exists():
        shutil.rmtree(TEMP_DATA_FOLDER, ignore_errors=True)

    html = HTML.replace("__LOGO__", logo_data_uri()).replace(
        "__DATA__", json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    )
    OUTPUT_HTML.write_text(html, encoding="utf-8")
    print("\nSTANDALONE DASHBOARD CREATED")
    print(f"Source: {builder.INPUT_FILE}")
    print(f"Output: {OUTPUT_HTML}")
    print("Open the HTML file in Chrome or Edge.")
    return OUTPUT_HTML


if __name__ == "__main__":
    generate_html()