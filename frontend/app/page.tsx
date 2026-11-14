import UploadPanel from "@/components/upload/UploadPanel";

export default function Home() {
  return (
    <div className="flex flex-col flex-1 items-center justify-start bg-zinc-50 font-sans dark:bg-black">
      <main className="flex w-full max-w-xl flex-col gap-8 px-4 py-12 sm:px-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-zinc-900 dark:text-zinc-100">
            Intelligence Forge
          </h1>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            Multimodal research knowledge retrieval and assistant
          </p>
        </div>

        <UploadPanel />
      </main>
    </div>
  );
}
