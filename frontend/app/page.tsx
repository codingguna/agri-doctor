import UploadForm from "../components/UploadForm";

export default function Home() {
  return (
    <main className="p-6">
      <p className="mx-auto mb-4 max-w-2xl text-center text-xs text-gray-500">
        SIH26131 • Govt of Maharashtra • Early detection and management of crop diseases and pest infestations
      </p>
      <UploadForm />
      <p className="mx-auto mt-4 max-w-2xl text-center text-xs text-gray-500">
        Backend: <code>/health</code> <code>/predict</code> <code>/diseases</code> — runs in mock mode until you train a model in <code>ml/</code>.
      </p>
    </main>
  );
}
