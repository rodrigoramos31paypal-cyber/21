(function () {
 'use strict';
 const empty = () => ({profileV4:null,foodPlan:null,mealChecks:{},shoppingChecks:{},checks:{},name:'',email:'',day:1,track:'geral',profileDone:false,userId:null,loggedIn:false,paid:false,syncPending:false,accountOwner:null});
 function transition(state, userId, saved, importGuest=false) {
  const guest = !state.accountOwner && importGuest ? {...state} : null;
  Object.assign(state, empty(), saved || guest || {});
  state.accountOwner=userId;
  state.profileDone=Boolean(state.profileV4);
  state.loggedIn=Boolean(userId);
  state.paid=false;
  state.userId=null;
  return state;
 }
 window.FocoAccounts={empty,transition};
})();
