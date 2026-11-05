/* Regras de organização: sem metas calóricas ou substituições de ingredientes. */
(function(root){
'use strict';
const meals={pequeno:'Pequeno-almoço',almoco:'Almoço',lanche:'Lanche',jantar:'Jantar'};
function compatible(recipe,profile,meal){
 if(meal&&!recipe.meals.includes(meal))return false;
 if(profile.otherRestrictions?.trim())return false;
 if(profile.diet==='vegan'&&recipe.diet!=='vegan')return false;
 if(profile.diet==='vegetariano'&&!['vegan','vegetariano'].includes(recipe.diet))return false;
 return !(profile.allergies||[]).some(a=>recipe.allergens.includes(a==='lactose'?'leite':a));
}
function candidates(recipes,profile,meal){
 const list=recipes.filter(r=>compatible(r,profile,meal));
 if(profile.goal==='perder')list.sort((a,b)=>a.nutrition.kcal-b.nutrition.kcal);
 if(profile.goal==='ganhar')list.sort((a,b)=>b.nutrition.kcal-a.nutrition.kcal);
 return list;
}
function createPlan(recipes,profile){
 return Array.from({length:21},(_,d)=>Object.fromEntries((profile.meals||Object.keys(meals)).map((m,i)=>{
 const list=candidates(recipes,profile,m); // Seleção curta, com repetição ao longo das três semanas.
 const pool=list.slice(0,3);return [m,pool.length?pool[(d+i)%pool.length].id:null];
 })));
}
function shopping(recipes,plan,week){
 const totals=new Map();
 for(const day of plan.slice(week*7,week*7+7))for(const id of Object.values(day)){
 const recipe=recipes.find(r=>r.id===id);if(!recipe)continue;
 for(const ing of recipe.ingredients){const key=JSON.stringify([ing.name,ing.unit,ing.qty===null]);
 if(!totals.has(key))totals.set(key,{...ing,notes:[],qty:ing.qty===null?null:0,maximum:ing.qty===null?null:0,count:0});
 const total=totals.get(key);total.count++;if(ing.note&&!total.notes.includes(ing.note))total.notes.push(ing.note);if(ing.qty!==null){total.qty+=ing.qty;total.maximum+=ing.maximum||ing.qty;}
 }}return [...totals.values()].map(i=>({...i,note:i.notes.join(' · ')})).sort((a,b)=>a.name.localeCompare(b.name,'pt'));
}
function quantity(i){const fmt=n=>Number(n.toFixed(1)).toLocaleString('pt-PT');return i.qty===null?`q.b. · ${i.count} ${i.count===1?'utilização':'utilizações'}`:`${fmt(i.qty)}${i.maximum!==i.qty?'–'+fmt(i.maximum):''} ${i.unit}`;}
root.FocoFood={meals,compatible,candidates,createPlan,shopping,quantity};
if(typeof module!=='undefined')module.exports=root.FocoFood;
})(typeof window!=='undefined'?window:globalThis);
