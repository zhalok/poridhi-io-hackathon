// app/search/page.tsx
'use client'

import React, { useState } from 'react'

/** full shape of each record */
interface DataItem {
  pair_id: string
  label: number
  id_left: number
  category_left: string
  cluster_id_left: number
  brand_left: string | null
  title_left: string
  description_left: string
  price_left: number | null
  specTableContent_left: any
  id_right: number
  category_right: string
  cluster_id_right: number
  brand_right: string | null
  title_right: string
  description_right: string
  price_right: number | null
  specTableContent_right: any
}

/** your sample object, duplicated to make “multiple” entries */
const sample: DataItem = {
  pair_id: '16965715#5931545',
  label: 1,
  id_left: 16965715,
  category_left: 'Camera_and_Photo',
  cluster_id_left: 9309675,
  brand_left: null,
  title_left:
    ' "Veho VCC-005 MUVI HD NPNG Body Camera/Action Camcorder Special Edition"@en " Consumer Video Cameras | Unique Photo "@en',
  description_left: `"
    HD video at 30fps & Up to 8MP Stills
    170 degree wide angle lens
    Includes a waterproof case: Up to 60m for 60 mins
    Rechargable li-ion battery up to 3hrs recording
    Includes 8GB Micro SD card (up to 32GB)
    1.5 inch viewfinder/review LCD, Touch panel control
    Self timer, digital zoom and noise activation
    Universal mounting options
    Standard tripod Mount
    Optional date and time stamp
    Dimensions (W x H x D): 47 x 80 x 19 mm
    Weight: 81 g
  "@en `,
  price_left: null,
  specTableContent_left: null,
  id_right: 5931545,
  category_right: 'Camera_and_Photo',
  cluster_id_right: 9309675,
  brand_right: '"Veho"@en-US',
  title_right:
    ' "Veho VCC-005-MUVI-NPNG MUVI HD Mini Handsfree ActionCam with Waterproof Case and 8 GB Memory - No Proof Glory Edition"@en-US "Sports & Action Video Cameras Page 7 | Come As You Arts"@en-US',
  description_right: `"... long description ... "@en-US `,
  price_right: null,
  specTableContent_right: null,
}

/** two copies to simulate “multiple” */
const dummyData: DataItem[] = [sample, sample]

const SearchPage: React.FC = () => {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<DataItem[]>([])
  const [searchClicked, setSearchClicked] = useState(false)

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    // here you could actually filter by query; for now we just show all that mention the query:
    const filtered = dummyData.filter(
      (item) =>
        item.title_left.toLowerCase().includes(query.toLowerCase()) ||
        item.title_right.toLowerCase().includes(query.toLowerCase())
    )
    setResults(filtered)
    setSearchClicked(true)
  }

  const truncate = (text: string) =>
    text.length > 30 ? text.slice(0, 30) + '…' : text

  /** flatten into simple entries for display */
  const entries = results.flatMap((item) => [
    {
      key: `L-${item.id_left}`,
      title: truncate(
        item.title_left.replace(/"@[^"]*"/g, '').trim()
      ),
      category: item.category_left,
      price: item.price_left,
    },
    {
      key: `R-${item.id_right}`,
      title: truncate(
        item.title_right.replace(/"@[^"]*"/g, '').trim()
      ),
      category: item.category_right,
      price: item.price_right,
    },
  ])

  return (
    <div className="min-h-screen flex flex-col items-center justify-center ">
      <form
  onSubmit={handleSearch}
  className="flex items-center space-x-2 bg-[#1E1E1E] px-4 py-3 rounded-lg w-full max-w-xl"
>
  <input
    type="text"
    placeholder="Ask anything..."
    value={query}
    onChange={(e) => setQuery(e.target.value)}
    className="flex-grow bg-transparent text-white placeholder-gray-400 focus:outline-none"
  />
  <button
    type="submit"
    className="px-4 py-2 bg-cyan-600 text-white rounded hover:bg-cyan-700 transition"
  >
    Search
  </button>
</form>


      {searchClicked && (
        <div className="mt-8 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6 p-4">
          {entries.map((entry) => (
            <div
              key={entry.key}
              className="bg-gray-900 shadow rounded-lg p-4"
            >
              <h2 className="font-semibold mb-2">{entry.title}</h2>
              <p className="text-sm text-gray-600">
                Category: {entry.category}
              </p>
              <p className="text-sm text-gray-600">
                Price:{' '}
                {entry.price !== null
                  ? `$${entry.price}`
                  : 'N/A'}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default SearchPage
