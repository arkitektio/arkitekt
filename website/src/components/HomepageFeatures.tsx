import useBaseUrl from "@docusaurus/useBaseUrl";
import React from "react";
import clsx from "clsx";
import styles from "./HomepageFeatures.module.css";

type FeatureItem = {
  title: string;
  image: string;
  description: JSX.Element;
};

const FeatureList: FeatureItem[] = [
  {
    title: "Easy to Use",
    image: "/img/undraw_docusaurus_mountain.svg",
    description: (
      <>
        arkitekt was designed to make the abstraction of remote procedure calls
        as unintrusive as possible.
      </>
    ),
  },
  {
    title: "Provisions",
    image: "/img/undraw_docusaurus_tree.svg",
    description: (
      <>
        Arkitekt takes care of auto providing and unproviding infrastructure,
        according to the users needs.
      </>
    ),
  },
  {
    title: "Powered by Async",
    image: "/img/undraw_docusaurus_react.svg",
    description: (
      <>
        arkitekt runs your code asynchronously, in different threads, processes,
        workers or even computers
      </>
    ),
  },
];

function Feature({ title, image, description }: FeatureItem) {
  return (
    <div className={clsx("col col--4")}>
      <div className="text--center padding-horiz--md padding-top--md">
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
    </div>
  );
}

export default function HomepageFeatures(): JSX.Element {
  return (
    <section className={styles.features}>
      <div className="container">
        <div className="row">
          {FeatureList.map((props, idx) => (
            <Feature key={idx} {...props} />
          ))}
        </div>
      </div>
    </section>
  );
}
