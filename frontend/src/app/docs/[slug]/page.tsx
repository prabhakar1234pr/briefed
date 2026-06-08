import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import LandingHeader from "@/components/LandingHeader";
import LandingFooter from "@/components/landing/LandingFooter";
import styles from "@/app/page.module.css";
import { articles, getArticle } from "../articles";

export function generateStaticParams() {
  return articles.map((article) => ({ slug: article.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const article = getArticle(slug);
  if (!article) return { title: "Docs · Agent Bora" };
  return { title: `${article.title} · Agent Bora`, description: article.excerpt };
}

export default async function ArticlePage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const article = getArticle(slug);
  if (!article) notFound();

  return (
    <div className={styles.page}>
      <LandingHeader />

      <article className={styles.article}>
        <Link href="/#docs" className={styles.articleBack}>
          ← Back to docs
        </Link>

        <span className={styles.articleTag}>{article.tag}</span>
        <h1 className={styles.articleTitle}>{article.title}</h1>
        <div className={styles.articleMeta}>
          <span>{article.date}</span>
          <span>·</span>
          <span>{article.readTime}</span>
        </div>

        <div className={styles.articleCover} style={{ background: article.gradient }}>
          <span>{article.emoji}</span>
        </div>

        <div className={styles.articleBody}>
          {article.body.map((block, idx) => {
            if (block.type === "h2") return <h2 key={idx}>{block.text}</h2>;
            if (block.type === "ul")
              return (
                <ul key={idx}>
                  {block.items.map((listItem) => (
                    <li key={listItem}>{listItem}</li>
                  ))}
                </ul>
              );
            return <p key={idx}>{block.text}</p>;
          })}
        </div>

        <div className={styles.articleFooter}>
          <h3>Ready to meet your AI teammate?</h3>
          <p>Create your first agent free and let Bora handle the rest.</p>
          <Link href="/auth?mode=signup" className={styles.buttonPrimary}>
            Create your agent
          </Link>
        </div>
      </article>

      <LandingFooter />
    </div>
  );
}
