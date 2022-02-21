(self.webpackChunkwebsite=self.webpackChunkwebsite||[]).push([[4847],{38281:function(n,i,t){"use strict";t.r(i),t.d(i,{frontMatter:function(){return u},contentTitle:function(){return k},metadata:function(){return l},toc:function(){return d},default:function(){return h}});var e=t(87462),r=t(63366),a=(t(67294),t(3905)),o=t(93456),s=["components"],u={sidebar_position:1,sidebar_label:"Design"},k="Design",l={unversionedId:"links/design",id:"links/design",title:"Design",description:"Rath is structured around links and their orchestration",source:"@site/docs/links/design.md",sourceDirName:"links",slug:"/links/design",permalink:"/arkitekt/docs/links/design",editUrl:"https://github.com/facebook/docusaurus/tree/main/packages/create-docusaurus/templates/shared/docs/links/design.md",tags:[],version:"current",sidebarPosition:1,frontMatter:{sidebar_position:1,sidebar_label:"Design"},sidebar:"tutorialSidebar",previous:{title:"Compose",permalink:"/arkitekt/docs/links/compose"},next:{title:"Split",permalink:"/arkitekt/docs/links/split"}},d=[{value:"Terminating Links",id:"terminating-links",children:[],level:3},{value:"Continuation Links",id:"continuation-links",children:[],level:3}],c={toc:d};function h(n){var i=n.components,t=(0,r.Z)(n,s);return(0,a.kt)("wrapper",(0,e.Z)({},c,t,{components:i,mdxType:"MDXLayout"}),(0,a.kt)("h1",{id:"design"},"Design"),(0,a.kt)("p",null,"Rath is structured around links and their orchestration"),(0,a.kt)(o.Mermaid,{chart:"flowchart LR;\n    id0(Query)--\x3e|Request|id1(Rath Client)\n    id1(Rath Client)--\x3e|Operation|id2(Continuation Link)\n    id2(Continuation Link)--\x3e|Operation|id3(Terminating Link)",mdxType:"Mermaid"}),(0,a.kt)("h3",{id:"terminating-links"},"Terminating Links"),(0,a.kt)("p",null,"Terminating Links make network requests to the underlying graphql\nendpoint."),(0,a.kt)("h3",{id:"continuation-links"},"Continuation Links"),(0,a.kt)("p",null,"Continuation Links take requests in form of operations and\nalter the request or introduce logic before a underlying request to\nthe endpoint."),(0,a.kt)("p",null,"As an example an Auth link"),(0,a.kt)(o.Mermaid,{chart:"sequenceDiagram\n    autonumber\n    participant Rath\n    participant AuthLink\n    participant TerminationLink\n    Rath->>AuthLink: Operation\n    AuthLink->>AuthLink: Get Token\n    AuthLink--\x3e>TerminationLink: Operation + Token\n    TerminationLink --\x3e> AuthLink: Result\n    AuthLink --\x3e> Rath: Result",mdxType:"Mermaid"}),(0,a.kt)("p",null,"The authlink can then on further store the auth token and append it to\nthe operation.\nThey can also handle complex failures"),(0,a.kt)(o.Mermaid,{chart:"sequenceDiagram\n    autonumber\n    participant Rath\n    participant AuthLink\n    participant TerminationLink\n    Rath->>AuthLink: Operation\n    AuthLink--\x3e>TerminationLink: Operation + Token\n    TerminationLink--XAuthLink: Error\n    AuthLink->>AuthLink: Refech Token\n    AuthLink--\x3e>TerminationLink: Operation + Refreshed Token\n    TerminationLink --\x3e> AuthLink: Result\n    AuthLink --\x3e> Rath: Result",mdxType:"Mermaid"}))}h.isMDXComponent=!0},11748:function(n,i,t){var e={"./locale":89234,"./locale.js":89234};function r(n){var i=a(n);return t(i)}function a(n){if(!t.o(e,n)){var i=new Error("Cannot find module '"+n+"'");throw i.code="MODULE_NOT_FOUND",i}return e[n]}r.keys=function(){return Object.keys(e)},r.resolve=a,n.exports=r,r.id=11748}}]);