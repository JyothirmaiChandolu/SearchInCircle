/** Flat list of recognizable skill/tool names used to scan resume text for suggestions.
 * Deliberately simple keyword matching, not an AI pipeline — the user reviews and edits
 * every suggestion before anything is saved (see Skill/Tag "DoD": nothing persists without
 * confirmation), so false positives here cost a user one extra uncheck, not a bad save. */
export const SKILL_DICTIONARY = [
  // Programming languages
  'JavaScript', 'TypeScript', 'Python', 'Java', 'C++', 'C#', 'Go', 'Rust', 'Ruby', 'PHP',
  'Swift', 'Kotlin', 'Scala', 'R', 'MATLAB', 'SQL', 'Bash', 'Shell Scripting', 'Perl',
  // Frontend
  'React', 'React Native', 'Vue', 'Angular', 'Next.js', 'HTML', 'CSS', 'Tailwind CSS',
  'Redux', 'GraphQL',
  // Backend / infra
  'Node.js', 'Express', 'NestJS', 'Django', 'Flask', 'Spring Boot', 'Ruby on Rails',
  'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'Docker', 'Kubernetes', 'AWS', 'Azure',
  'Google Cloud', 'Terraform', 'CI/CD', 'Linux',
  // Data / AI
  'Machine Learning', 'Deep Learning', 'Data Analysis', 'Data Science', 'Pandas', 'NumPy',
  'TensorFlow', 'PyTorch', 'Excel', 'Power BI', 'Tableau',
  // Design
  'Figma', 'Adobe Photoshop', 'Adobe Illustrator', 'UI Design', 'UX Design', 'Sketch',
  // Product / management
  'Project Management', 'Product Management', 'Agile', 'Scrum', 'JIRA', 'Business Analysis',
  // Writing / marketing
  'Content Writing', 'Copywriting', 'SEO', 'Social Media Marketing', 'Email Marketing',
  // General office
  'Microsoft Word', 'Microsoft Excel', 'Microsoft PowerPoint', 'Google Sheets', 'Salesforce',
  // Trades / services
  'Carpentry', 'Plumbing', 'Electrical Wiring', 'Welding', 'Cooking', 'Baking', 'Tailoring',
  'Photography', 'Videography', 'Video Editing',
  // Languages (as a spoken skill, distinct from programming)
  'Spanish', 'French', 'German', 'Mandarin', 'Hindi', 'Tamil', 'Telugu',
  // Soft skills
  'Public Speaking', 'Negotiation', 'Leadership', 'Customer Service', 'Teaching',
];
