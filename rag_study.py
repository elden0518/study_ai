# 1. 导入需要的包
from langchain.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.llms import HuggingFacePipeline

# ----------------------
# 步骤1：准备你的文档（知识库）
# ----------------------
# 这里我们直接用一段文字当知识库，你也可以换成自己的 txt 文件
document = """
人工智能（AI）是一门让机器模拟人类智能的技术。
RAG 的全称是 Retrieval-Augmented Generation，检索增强生成。
RAG 的作用是让大模型先查资料，再回答问题，避免胡说八道。
RAG 分为三个步骤：文档分块、向量化存储、检索、生成答案。
常用的 RAG 类型有：基础 RAG、高级 RAG、自适应 RAG。
"""

# 把文字保存成临时文件
with open("rag_knowledge.txt", "w", encoding="utf-8") as f:
    f.write(document)

# 加载文档
loader = TextLoader("rag_knowledge.txt", encoding="utf-8")
docs = loader.load()

# ----------------------
# 步骤2：把文档切分成小块
# ----------------------
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=100,  # 每块大小
    chunk_overlap=20, # 重叠部分
)
texts = text_splitter.split_documents(docs)

# ----------------------
# 步骤3：向量化 + 存入向量库
# ----------------------
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# 建立 FAISS 向量库
db = FAISS.from_documents(texts, embeddings)

# ----------------------
# 步骤4：创建 RAG 检索器
# ----------------------
retriever = db.as_retriever(search_kwargs={"k": 2})

# ----------------------
# 步骤5：用一个轻量模型做问答
# ----------------------
from langchain.llms import FakeListLLM
# 这里用一个简易模拟LLM，真实场景可以换成通义千问、文心一言、GPT等
llm = FakeListLLM(responses=[
    "RAG 的全称是 Retrieval-Augmented Generation，也就是检索增强生成。",
    "RAG 分为三个步骤：文档分块、向量化存储、检索、生成答案。"
])

# ----------------------
# 步骤6：创建 RAG 问答链
# ----------------------
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=retriever,
    return_source_documents=True
)

# ----------------------
# 开始提问！
# ----------------------
print("=== RAG 问答系统 ===")
question = "RAG 是什么？"
print("你的问题：", question)

result = qa_chain({"query": question})
print("\n【AI 回答】：")
print(result["result"])

print("\n【参考资料】：")
for doc in result["source_documents"]:
    print("-", doc.page_content)