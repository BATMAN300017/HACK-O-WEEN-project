import Link from 'next/link';

type PlaceholderPageProps = {
  title: string;
};

export default function PlaceholderPage({ title }: PlaceholderPageProps) {
  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-3xl font-bold tracking-tight text-slate-900">{title}</h1>
      <p className="mt-4 text-slate-600" role="status">
        This screen has not been implemented yet.
      </p>
      <Link className="mt-6 inline-block text-sky-700 hover:underline" href="/dashboard">
        Return to dashboard
      </Link>
    </main>
  );
}
