(self.webpackChunkwebsite=self.webpackChunkwebsite||[]).push([[5715],{11953:function(e,o,t){"use strict";t.r(o),t.d(o,{frontMatter:function(){return c},contentTitle:function(){return l},metadata:function(){return d},toc:function(){return p},default:function(){return v}});var r=t(87462),n=t(63366),i=(t(67294),t(3905)),s=t(93456),a=["components"],c={sidebar_position:1,sidebar_label:"Design"},l="Design",d={unversionedId:"protocol/design",id:"protocol/design",title:"Design",description:"Arkitekt provides to major abstractions for your clients.",source:"@site/docs/protocol/design.md",sourceDirName:"protocol",slug:"/protocol/design",permalink:"/arkitekt/docs/protocol/design",editUrl:"https://github.com/facebook/docusaurus/tree/main/packages/create-docusaurus/templates/shared/docs/protocol/design.md",tags:[],version:"current",sidebarPosition:1,frontMatter:{sidebar_position:1,sidebar_label:"Design"},sidebar:"tutorialSidebar",previous:{title:"Split",permalink:"/arkitekt/docs/links/split"},next:{title:"First Reservation (no provision)",permalink:"/arkitekt/docs/protocol/reserve/no_provision"}},p=[{value:"Reservations",id:"reservations",children:[{value:"For example:",id:"for-example",children:[],level:4}],level:2},{value:"Provisions",id:"provisions",children:[],level:2},{value:"Decision Tree for Protocol",id:"decision-tree-for-protocol",children:[],level:2}],k={toc:p};function v(e){var o=e.components,t=(0,n.Z)(e,a);return(0,i.kt)("wrapper",(0,r.Z)({},k,t,{components:o,mdxType:"MDXLayout"}),(0,i.kt)("h1",{id:"design"},"Design"),(0,i.kt)("p",null,"Arkitekt provides to major abstractions for your clients.\n",(0,i.kt)("strong",{parentName:"p"},"Provisions")," and ",(0,i.kt)("strong",{parentName:"p"},"Reservation")),(0,i.kt)("h2",{id:"reservations"},"Reservations"),(0,i.kt)("p",null,(0,i.kt)("strong",{parentName:"p"},"Reservations")," are contracts that you have with arkitekt. They describe\nwhich node you want to use with what parallelization strategy."),(0,i.kt)("h4",{id:"for-example"},"For example:"),(0,i.kt)("p",null,"You have a connected app that ",(0,i.kt)("em",{parentName:"p"},"provides")," a node to convolve an image. In order\nto use it you first ",(0,i.kt)("em",{parentName:"p"},"reserve")," that node and then you can ",(0,i.kt)("em",{parentName:"p"},"assign")," tasks to it."),(0,i.kt)("h2",{id:"provisions"},"Provisions"),(0,i.kt)("p",null,(0,i.kt)("strong",{parentName:"p"},"Provisions")," are contracts that you need to fullfill as a client app.\nIf you register to be able to provide for a nodeyou need to listen to the waiter endpoint and accept provisions and mark them active."),(0,i.kt)("div",{className:"admonition admonition-tip alert alert--success"},(0,i.kt)("div",{parentName:"div",className:"admonition-heading"},(0,i.kt)("h5",{parentName:"div"},(0,i.kt)("span",{parentName:"h5",className:"admonition-icon"},(0,i.kt)("svg",{parentName:"span",xmlns:"http://www.w3.org/2000/svg",width:"12",height:"16",viewBox:"0 0 12 16"},(0,i.kt)("path",{parentName:"svg",fillRule:"evenodd",d:"M6.5 0C3.48 0 1 2.19 1 5c0 .92.55 2.25 1 3 1.34 2.25 1.78 2.78 2 4v1h5v-1c.22-1.22.66-1.75 2-4 .45-.75 1-2.08 1-3 0-2.81-2.48-5-5.5-5zm3.64 7.48c-.25.44-.47.8-.67 1.11-.86 1.41-1.25 2.06-1.45 3.23-.02.05-.02.11-.02.17H5c0-.06 0-.13-.02-.17-.2-1.17-.59-1.83-1.45-3.23-.2-.31-.42-.67-.67-1.11C2.44 6.78 2 5.65 2 5c0-2.2 2.02-4 4.5-4 1.22 0 2.36.42 3.22 1.19C10.55 2.94 11 3.94 11 5c0 .66-.44 1.78-.86 2.48zM4 14h5c-.23 1.14-1.3 2-2.5 2s-2.27-.86-2.5-2z"}))),"tip")),(0,i.kt)("div",{parentName:"div",className:"admonition-content"},(0,i.kt)("p",{parentName:"div"},"You can of course decide to never register templates and use the\napp as a pure client. But if you do, you should make sure you fullfill your\nprovisions."))),(0,i.kt)("h2",{id:"decision-tree-for-protocol"},"Decision Tree for Protocol"),(0,i.kt)(s.Mermaid,{chart:'flowchart TD\n    A[Start]--\x3eB[Agent online]\n    B---\x3e|Yes| C[Provided Before]\n    B---\x3e|No| D[Provided Before]\n    C---\x3e|Yes| E[Reserved Before]\n    C---\x3e|No| F[Reserved Before]\n    D---\x3e|Yes| G[Reserved Before]\n    D---\x3e|No| H[Reserved Before]\n    E---\x3e|Yes| I[Clickme]\n    E---\x3e|No| J[Clickme]\n    F---\x3e|Yes| K[Clickme]\n    F---\x3e|No| L[Clickme]\n    G---\x3e|Yes| M[Clickme]\n    G---\x3e|No| N[Clickme]\n    H---\x3e|Yes| O[Clickme]\n    H---\x3e|No| P[Clickme]\n\n\n    click I href "/arkitekt/docs/protocol/reserve/no_provision"\n    click J href "/arkitekt/docs/protocol/reserve/no_provision"\n    click K href "/arkitekt/docs/protocol/reserve/no_provision"\n    click L href "/arkitekt/docs/protocol/reserve/no_provision"\n    click M href "/arkitekt/docs/protocol/reserve/no_provision"\n    click N href "/arkitekt/docs/protocol/reserve/no_provision"\n    click O href "/arkitekt/docs/protocol/reserve/no_provision"\n    click P href "/arkitekt/docs/protocol/reserve/no_provision"\n',mdxType:"Mermaid"}))}v.isMDXComponent=!0},11748:function(e,o,t){var r={"./locale":89234,"./locale.js":89234};function n(e){var o=i(e);return t(o)}function i(e){if(!t.o(r,e)){var o=new Error("Cannot find module '"+e+"'");throw o.code="MODULE_NOT_FOUND",o}return r[e]}n.keys=function(){return Object.keys(r)},n.resolve=i,e.exports=n,n.id=11748}}]);