export type ThumbColor = "lime" | "magenta" | "cyan" | "amber" | "red" | "violet"

export interface LibraryItem {
  id: string
  name: string
  trick: string
  duration: number
  date: string
  color: ThumbColor
  videoUrl?: string
  analysisUrl?: string
}

export const LIBRARY: LibraryItem[] = [
  {
    id: "fs180-001",
    name: "fs180_rtl_land_001.mp4",
    trick: "frontside 180",
    duration: 2.7,
    date: "bundled",
    color: "lime",
    videoUrl: "/fs180_rtl_land_001.mp4",
    analysisUrl: "/fs180_rtl_land_001_analysis.json"
  },
  {
    id: "bs180",
    name: "bs180_rtl_land_001.mp4",
    trick: "backside 180",
    duration: 2.77,
    color: "lime",
    date: "bundled",
    videoUrl: "/bs180_rtl_land_001.mp4",
    analysisUrl: "/bs180_rtl_land_001.json"
  },
  {
    id: "kickflip-001",
    name: "kickflip_ltr_land_001.mp4",
    trick: "kickflip",
    duration: 1.74,
    date: "bundled",
    color: "lime",
    videoUrl: "/kickflip_ltr_land_001.mp4",
    analysisUrl: "/kickflip_ltr_land_001.json"
  },
  {
    id: "heelflip-001",
    name: "heelflip_rtl_almost_001.mp4",
    trick: "heelflip",
    duration: 2.23,
    date: "bundled",
    color: "amber",
    videoUrl: "/heelflip_rtl_almost_001.mp4",
    analysisUrl: "/heelflip_rtl_almost_001.json"
  },
  {
    id: "fs-pop-shuvit",
    name: "fs-pop-shove-it_ltr_land_001.mp4",
    trick: "FS pop shuvit",
    duration: 1.41,
    date: "bundled",
    color: "cyan",
    videoUrl: "/fs-pop-shove-it_ltr_land_001.mp4",
    analysisUrl: "/fs-pop-shove-it_ltr_land_001.json"
  },
  {
    id: "manual",
    name: "ollie-to-manual-on-the-box_rtl_land_001.mp4",
    trick: "manual",
    duration: 2.26,
    date: "bad",
    color: "magenta",
    videoUrl: "/ollie-to-manual-on-the-box_rtl_land_001.mp4",
    analysisUrl: "/ollie-to-manual-on-the-box_rtl_land_001.json"
  },
  {
    id: "ollie-kickflip",
    name: "ollie-on-the-box-bs-kickturn-kickflip-out_rtl-away_land_001.mp4",
    trick: "ollie-kickflip",
    duration: 5.8,
    date: "bad",
    color: "magenta",
    videoUrl: "/ollie-on-the-box-bs-kickturn-kickflip-out_rtl-away_land_001.mp4",
    analysisUrl: "/ollie-on-the-box-bs-kickturn-kickflip-out_rtl-away_land_001.json"
  },
  {
    id: "nose-slide",
    name: "nose-slide_rtl-towards_land_002.mp4",
    trick: "nose slide",
    duration: 2.33,
    date: "bad",
    color: "magenta",
    videoUrl: "/nose-slide_rtl-towards_land_002.mp4",
    analysisUrl: "/nose-slide_rtl-towards_land_002.json"
  },
  {
    id: "treflip",
    name: "treflip_rtl_land_001.mp4",
    trick: "treflip",
    duration: 3.15,
    date: "bad",
    color: "red",
    videoUrl: "/treflip_rtl_land_001.mp4",
    analysisUrl: "/treflip_rtl_land_001.json"
  }
]
