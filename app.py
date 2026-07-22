from flask import Flask, request, jsonify
from flask_cors import CORS
from rag import ask_video,load_video
import traceback

app = Flask(__name__)
CORS(app)

@app.route("/load_video",methods=['POST'])
def load():
    data=request.json
    video_id=data.get('video_id')
    if not video_id:
        return jsonify({"error":'video_id is missing'}),400
    result=load_video(video_id)
    return jsonify({"message":result})


@app.route("/ask", methods=["POST"])
def ask():

    try:
        data = request.get_json()

        print("Received:", data)

        video_id = data["video_id"]
        question = data["question"]

        answer = ask_video(
            video_id,
            question
        )

        return jsonify({
            "answer": answer
        })


    except Exception as e:

        print("ERROR OCCURRED:")
        traceback.print_exc()

        return jsonify({
            "error": str(e)
        }), 500


if __name__ == "__main__":
    app.run(debug=True,use_reloader=False)