"use strict";(self.webpackChunkwebsite=self.webpackChunkwebsite||[]).push([[7218],{3905:function(e,t,r){r.d(t,{Zo:function(){return l},kt:function(){return d}});var n=r(67294);function i(e,t,r){return t in e?Object.defineProperty(e,t,{value:r,enumerable:!0,configurable:!0,writable:!0}):e[t]=r,e}function a(e,t){var r=Object.keys(e);if(Object.getOwnPropertySymbols){var n=Object.getOwnPropertySymbols(e);t&&(n=n.filter((function(t){return Object.getOwnPropertyDescriptor(e,t).enumerable}))),r.push.apply(r,n)}return r}function o(e){for(var t=1;t<arguments.length;t++){var r=null!=arguments[t]?arguments[t]:{};t%2?a(Object(r),!0).forEach((function(t){i(e,t,r[t])})):Object.getOwnPropertyDescriptors?Object.defineProperties(e,Object.getOwnPropertyDescriptors(r)):a(Object(r)).forEach((function(t){Object.defineProperty(e,t,Object.getOwnPropertyDescriptor(r,t))}))}return e}function u(e,t){if(null==e)return{};var r,n,i=function(e,t){if(null==e)return{};var r,n,i={},a=Object.keys(e);for(n=0;n<a.length;n++)r=a[n],t.indexOf(r)>=0||(i[r]=e[r]);return i}(e,t);if(Object.getOwnPropertySymbols){var a=Object.getOwnPropertySymbols(e);for(n=0;n<a.length;n++)r=a[n],t.indexOf(r)>=0||Object.prototype.propertyIsEnumerable.call(e,r)&&(i[r]=e[r])}return i}var c=n.createContext({}),s=function(e){var t=n.useContext(c),r=t;return e&&(r="function"==typeof e?e(t):o(o({},t),e)),r},l=function(e){var t=s(e.components);return n.createElement(c.Provider,{value:t},e.children)},p={inlineCode:"code",wrapper:function(e){var t=e.children;return n.createElement(n.Fragment,{},t)}},f=n.forwardRef((function(e,t){var r=e.components,i=e.mdxType,a=e.originalType,c=e.parentName,l=u(e,["components","mdxType","originalType","parentName"]),f=s(r),d=i,b=f["".concat(c,".").concat(d)]||f[d]||p[d]||a;return r?n.createElement(b,o(o({ref:t},l),{},{components:r})):n.createElement(b,o({ref:t},l))}));function d(e,t){var r=arguments,i=t&&t.mdxType;if("string"==typeof e||i){var a=r.length,o=new Array(a);o[0]=f;var u={};for(var c in t)hasOwnProperty.call(t,c)&&(u[c]=t[c]);u.originalType=e,u.mdxType="string"==typeof e?e:i,o[1]=u;for(var s=2;s<a;s++)o[s]=r[s];return n.createElement.apply(null,o)}return n.createElement.apply(null,r)}f.displayName="MDXCreateElement"},40103:function(e,t,r){r.r(t),r.d(t,{frontMatter:function(){return u},contentTitle:function(){return c},metadata:function(){return s},toc:function(){return l},default:function(){return f}});var n=r(87462),i=r(63366),a=(r(67294),r(3905)),o=["components"],u={sidebar_label:"base",title:"ui.qtwidgets.base"},c=void 0,s={unversionedId:"reference/ui/qtwidgets/base",id:"reference/ui/qtwidgets/base",title:"ui.qtwidgets.base",description:"UIPortMixin Objects",source:"@site/docs/reference/ui/qtwidgets/base.md",sourceDirName:"reference/ui/qtwidgets",slug:"/reference/ui/qtwidgets/base",permalink:"/rath/docs/reference/ui/qtwidgets/base",editUrl:"https://github.com/facebook/docusaurus/tree/main/packages/create-docusaurus/templates/shared/docs/reference/ui/qtwidgets/base.md",tags:[],version:"current",frontMatter:{sidebar_label:"base",title:"ui.qtwidgets.base"},sidebar:"tutorialSidebar",previous:{title:"registry",permalink:"/rath/docs/reference/ui/registry"},next:{title:"qtlistsearchwidget",permalink:"/rath/docs/reference/ui/qtwidgets/qtlistsearchwidget"}},l=[{value:"UIPortMixin Objects",id:"uiportmixin-objects",children:[{value:"get_current_value",id:"get_current_value",children:[],level:4}],level:2}],p={toc:l};function f(e){var t=e.components,r=(0,i.Z)(e,o);return(0,a.kt)("wrapper",(0,n.Z)({},p,r,{components:t,mdxType:"MDXLayout"}),(0,a.kt)("h2",{id:"uiportmixin-objects"},"UIPortMixin Objects"),(0,a.kt)("pre",null,(0,a.kt)("code",{parentName:"pre",className:"language-python"},"class UIPortMixin()\n")),(0,a.kt)("h4",{id:"get_current_value"},"get","_","current","_","value"),(0,a.kt)("pre",null,(0,a.kt)("code",{parentName:"pre",className:"language-python"},"@abstractmethod\ndef get_current_value()\n")),(0,a.kt)("p",null,"Gets the current value of the widget or returns None if\nno user input was set, or default"),(0,a.kt)("p",null,(0,a.kt)("strong",{parentName:"p"},"Raises"),":"),(0,a.kt)("ul",null,(0,a.kt)("li",{parentName:"ul"},(0,a.kt)("inlineCode",{parentName:"li"},"NoValueSetError")," - An error that this widgets has no current value set")))}f.isMDXComponent=!0}}]);