"use strict";(self.webpackChunkwebsite=self.webpackChunkwebsite||[]).push([[7898],{3905:function(e,t,n){n.d(t,{Zo:function(){return i},kt:function(){return d}});var r=n(67294);function a(e,t,n){return t in e?Object.defineProperty(e,t,{value:n,enumerable:!0,configurable:!0,writable:!0}):e[t]=n,e}function o(e,t){var n=Object.keys(e);if(Object.getOwnPropertySymbols){var r=Object.getOwnPropertySymbols(e);t&&(r=r.filter((function(t){return Object.getOwnPropertyDescriptor(e,t).enumerable}))),n.push.apply(n,r)}return n}function c(e){for(var t=1;t<arguments.length;t++){var n=null!=arguments[t]?arguments[t]:{};t%2?o(Object(n),!0).forEach((function(t){a(e,t,n[t])})):Object.getOwnPropertyDescriptors?Object.defineProperties(e,Object.getOwnPropertyDescriptors(n)):o(Object(n)).forEach((function(t){Object.defineProperty(e,t,Object.getOwnPropertyDescriptor(n,t))}))}return e}function s(e,t){if(null==e)return{};var n,r,a=function(e,t){if(null==e)return{};var n,r,a={},o=Object.keys(e);for(r=0;r<o.length;r++)n=o[r],t.indexOf(n)>=0||(a[n]=e[n]);return a}(e,t);if(Object.getOwnPropertySymbols){var o=Object.getOwnPropertySymbols(e);for(r=0;r<o.length;r++)n=o[r],t.indexOf(n)>=0||Object.prototype.propertyIsEnumerable.call(e,n)&&(a[n]=e[n])}return a}var l=r.createContext({}),u=function(e){var t=r.useContext(l),n=t;return e&&(n="function"==typeof e?e(t):c(c({},t),e)),n},i=function(e){var t=u(e.components);return r.createElement(l.Provider,{value:t},e.children)},f={inlineCode:"code",wrapper:function(e){var t=e.children;return r.createElement(r.Fragment,{},t)}},p=r.forwardRef((function(e,t){var n=e.components,a=e.mdxType,o=e.originalType,l=e.parentName,i=s(e,["components","mdxType","originalType","parentName"]),p=u(n),d=a,g=p["".concat(l,".").concat(d)]||p[d]||f[d]||o;return n?r.createElement(g,c(c({ref:t},i),{},{components:n})):r.createElement(g,c({ref:t},i))}));function d(e,t){var n=arguments,a=t&&t.mdxType;if("string"==typeof e||a){var o=n.length,c=new Array(o);c[0]=p;var s={};for(var l in t)hasOwnProperty.call(t,l)&&(s[l]=t[l]);s.originalType=e,s.mdxType="string"==typeof e?e:a,c[1]=s;for(var u=2;u<o;u++)c[u]=n[u];return r.createElement.apply(null,c)}return r.createElement.apply(null,n)}p.displayName="MDXCreateElement"},42175:function(e,t,n){n.r(t),n.d(t,{frontMatter:function(){return s},contentTitle:function(){return l},metadata:function(){return u},toc:function(){return i},default:function(){return p}});var r=n(87462),a=n(63366),o=(n(67294),n(3905)),c=["components"],s={sidebar_label:"stateful",title:"agents.stateful"},l=void 0,u={unversionedId:"reference/agents/stateful",id:"reference/agents/stateful",title:"agents.stateful",description:"StatefulAgent Objects",source:"@site/docs/reference/agents/stateful.md",sourceDirName:"reference/agents",slug:"/reference/agents/stateful",permalink:"/rath/docs/reference/agents/stateful",editUrl:"https://github.com/facebook/docusaurus/tree/main/packages/create-docusaurus/templates/shared/docs/reference/agents/stateful.md",tags:[],version:"current",frontMatter:{sidebar_label:"stateful",title:"agents.stateful"},sidebar:"tutorialSidebar",previous:{title:"standard",permalink:"/rath/docs/reference/agents/standard"},next:{title:"base",permalink:"/rath/docs/reference/agents/transport/base"}},i=[{value:"StatefulAgent Objects",id:"statefulagent-objects",children:[],level:2}],f={toc:i};function p(e){var t=e.components,n=(0,a.Z)(e,c);return(0,o.kt)("wrapper",(0,r.Z)({},f,n,{components:t,mdxType:"MDXLayout"}),(0,o.kt)("h2",{id:"statefulagent-objects"},"StatefulAgent Objects"),(0,o.kt)("pre",null,(0,o.kt)("code",{parentName:"pre",className:"language-python"},"class StatefulAgent(BaseAgent)\n")),(0,o.kt)("p",null,"An agent that tries to recover and\ntake care of all the assignations and provisions"),(0,o.kt)("p",null,(0,o.kt)("strong",{parentName:"p"},"Arguments"),":"),(0,o.kt)("ul",null,(0,o.kt)("li",{parentName:"ul"},(0,o.kt)("inlineCode",{parentName:"li"},"BaseAgent")," ",(0,o.kt)("strong",{parentName:"li"},"type")," - ",(0,o.kt)("em",{parentName:"li"},"description"))))}p.isMDXComponent=!0}}]);