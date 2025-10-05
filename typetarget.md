## factCardSchema.ts
```typescript
import { z } from "zod";

export const factCardSchema = z.object({
    id: z.string().optional(),
    language: z.string(),
    front: z.string(),
    back: z.string(),
    notes: z.array(z.string()).optional(),
    priority: z.number().optional()
})```

## goalSchema.ts
```typescript
import { z } from "zod";

export const goalSchema = z.object({
    id: z.string().optional(),
    language: z.string(),
    title: z.string(),
    priority: z.number().optional(),
    subGoals: z.array(z.string()).optional(),
    vocab: z.array(z.string()).optional(),
    factCards: z.array(z.string()).optional(),
    notes: z.array(z.string()).optional(),
})```

## immersionContentSchema.ts
```typescript
import { z } from "zod";

export const immersionContentSchema = z.object({
    id: z.string().optional(),
    language: z.string(),
    title: z.string(),
    content: z.string().optional(),
    priority: z.number().optional(),
    link: z.string().optional(),
    neededVocab: z.array(z.string()).optional(),
    notes: z.array(z.string()).optional(),
})```

## linkSchema.ts
```typescript
import { z } from "zod";

export const linkSchema = z.object({
    id: z.string().optional(),
    label: z.string(),
    url: z.string(),
    owner: z.string().optional(),
    ownerLink: z.string().optional(),
    license: z.string().optional(),
})```

## noteSchema.ts
```typescript
import { z } from "zod";

export const noteSchema = z.object({
    id: z.string().optional(),
    content: z.string(),
    showBeforeExercice: z.boolean().optional(),
    noteType: z.string().optional(),
})```

## resourceSchema.ts
```typescript
import { z } from "zod";

export const resourceSchema = z.object({
    id: z.string().optional(),
    isImmersionContent: z.boolean(),
    language: z.string(),
    title: z.string(),
    content: z.string().optional(),
    priority: z.number().optional(),
    link: z.string().optional(),
    notes: z.array(z.string()).optional(),
    vocab: z.array(z.string()).optional(),
    factCards: z.array(z.string()).optional(),
})```

## translationSchema.ts
```typescript
import { z } from "zod";

export const translationSchema = z.object({
    id: z.string().optional(),
    content: z.string(),
    notes: z.array(z.string()).optional(),
    priority: z.number().optional()
})```

## vocabSchema.ts
```typescript
import { z } from "zod";

const remoteVocabImageSchema = z.object({
    filename: z.string(),
    alt: z.string().optional(),
    tags: z.array(z.string()).optional()
});

const remoteVocabSoundSchema = z.object({
    filename: z.string()
});

export const vocabSchema = z.object({
    id: z.string().optional(),
    language: z.string(),
    content: z.string(),
    consideredCharacter: z.boolean().optional(),
    consideredSentence: z.boolean().optional(),
    consideredWord: z.boolean().optional(),
    notes: z.array(z.string()).optional(),
    transcriptions: z.array(z.string()).optional(),
    translations: z.array(z.string()).optional(),
    links: z.array(z.string()).optional(),
    relatedVocab: z.array(z.string()).optional(),
    notRelatedVocab: z.array(z.string()).optional(),
    contains: z.array(z.string()).optional(),
    similarSoundingButNotTheSame: z.array(z.string()).optional(),
    priority: z.number().optional(),
    isPicturable: z.boolean().optional(),
    images: z.array(remoteVocabImageSchema).optional(),
    sounds: z.array(remoteVocabSoundSchema).optional(),
    notInterestedInPronunciationOrAlreadyAdded: z.boolean().optional()
})```

